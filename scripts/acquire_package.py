#!/usr/bin/env python3
"""Search APKPure, resolve public download pages, and acquire verified APK/XAPK carriers."""
import argparse
from datetime import datetime, timezone
import hashlib
from html.parser import HTMLParser
import http.client
import json
from pathlib import Path
import re
import shutil
import sys
import tempfile
import time
import urllib.error
import urllib.parse
import urllib.request
import zipfile

PACKAGE = re.compile(r'[A-Za-z_]\w*(?:\.[A-Za-z_]\w*)+', re.ASCII)
PAGE_LIMIT = 4 * 1024**2
USER_AGENT = 'REA-GP/1.0 (public Android package acquisition)'


class AcquisitionError(ValueError):
    pass


def checked_url(value):
    parts = urllib.parse.urlsplit(value)
    if parts.scheme not in ('http', 'https') or not parts.hostname or parts.username or parts.password:
        raise AcquisitionError('Use an HTTP(S) URL without embedded credentials')
    return urllib.parse.urlunsplit(parts._replace(fragment=''))


def public_url(value):
    parts = urllib.parse.urlsplit(value)
    query = [(key, val if key in ('q', 'version') else '[redacted]')
             for key, val in urllib.parse.parse_qsl(parts.query, keep_blank_values=True)]
    return urllib.parse.urlunsplit(parts._replace(query=urllib.parse.urlencode(query), fragment=''))


class Redirects(urllib.request.HTTPRedirectHandler):
    max_redirections = 5
    max_repeats = 2

    def redirect_request(self, req, fp, code, msg, headers, newurl):
        newurl = checked_url(newurl)
        if req.type == 'https' and urllib.parse.urlsplit(newurl).scheme != 'https':
            raise AcquisitionError('Refusing an HTTPS-to-HTTP redirect')
        return super().redirect_request(req, fp, code, msg, headers, newurl)


def open_url(url, timeout, source_page=None):
    headers = {'User-Agent': USER_AGENT, 'Accept-Encoding': 'identity'}
    if source_page:
        page = urllib.parse.urlsplit(checked_url(source_page))
        headers['Referer'] = urllib.parse.urlunsplit(page._replace(query='', fragment=''))
    request = urllib.request.Request(checked_url(url), headers=headers)
    try:
        response = urllib.request.build_opener(Redirects()).open(request, timeout=timeout)
    except urllib.error.HTTPError as exc:
        exc.close()
        raise
    if response.status != 200:
        response.close()
        raise AcquisitionError('Expected HTTP 200; partial responses are not resumed')
    if response.headers.get('Content-Encoding', 'identity').lower() != 'identity':
        response.close()
        raise AcquisitionError('Unexpected content encoding; request an unencoded response')
    return response


class Page(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.links, self.structured, self.text = [], [], []
        self.anchor = None
        self.script = None
        self.script_depth = 0

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag == 'script':
            self.script_depth += 1
            if attrs.get('type', '').lower() == 'application/ld+json':
                self.script = []
        elif tag == 'a':
            self.anchor = {'attrs': attrs, 'parts': []}

    def handle_data(self, value):
        if self.script_depth:
            if self.script is not None:
                self.script.append(value)
            return
        self.text.append(value)
        if self.anchor is not None:
            self.anchor['parts'].append(value)

    def handle_endtag(self, tag):
        if tag == 'script':
            if self.script is not None:
                try:
                    self.structured.append(json.loads(''.join(self.script)))
                except (ValueError, TypeError):
                    pass
                self.script = None
            self.script_depth = max(0, self.script_depth - 1)
        elif tag == 'a' and self.anchor is not None:
            self.anchor['text'] = ' '.join(' '.join(self.anchor.pop('parts')).split())
            self.links.append(self.anchor)
            self.anchor = None


def read_page(url, timeout):
    with open_url(url, timeout) as response:
        body = response.read(PAGE_LIMIT + 1)
        if len(body) > PAGE_LIMIT:
            raise AcquisitionError('Page exceeds the 4 MiB parsing limit')
        content = body.decode(response.headers.get_content_charset() or 'utf-8', errors='replace')
        final_url = checked_url(response.geturl())
    page = Page()
    page.feed(content)
    return page, final_url


def apkpure_host(host):
    return any(host == domain or host.endswith('.' + domain) for domain in ('apkpure.net', 'apkpure.com'))


def page_package(url):
    parts = urllib.parse.urlsplit(url)
    if not apkpure_host(parts.hostname or ''):
        raise AcquisitionError('This resolver accepts APKPure pages; use fetch for an observed direct URL')
    matches = [part for part in parts.path.split('/') if PACKAGE.fullmatch(part)]
    if len(matches) != 1:
        raise AcquisitionError('Select a specific app/version page with a package ID in its path')
    return matches[0]


def search(query, timeout, limit):
    url = 'https://apkpure.net/search?' + urllib.parse.urlencode({'q': query})
    page, final_url = read_page(url, timeout)
    results, seen = [], set()
    for link in page.links:
        attrs = link['attrs']
        package = (attrs.get('data-dt-pkg') or '')
        if not PACKAGE.fullmatch(package) or package in seen:
            continue
        target = checked_url(urllib.parse.urljoin(final_url, attrs.get('href', '')))
        if not apkpure_host(urllib.parse.urlsplit(target).hostname or ''):
            continue
        if page_package(target) != package:
            continue
        seen.add(package)
        results.append({'name': attrs.get('title') or link['text'], 'package_id': package,
                        'listing_text': link['text'], 'page_url': target})
        if len(results) >= limit:
            break
    return {'status': 'candidates' if results else 'no_structured_results', 'query': query,
            'search_url': final_url, 'candidates': results,
            'next_step': 'Confirm identity/developer and version before fetching. If empty, use host web search/browser.'}


def json_objects(value):
    if isinstance(value, dict):
        yield value
        for child in value.values():
            yield from json_objects(child)
    elif isinstance(value, list):
        for child in value:
            yield from json_objects(child)


def resolve(url, timeout):
    expected = page_package(url)
    page, final_url = read_page(url, timeout)
    if page_package(final_url) != expected:
        raise AcquisitionError('Redirect changed the selected package')
    downloads = {}
    for link in page.links:
        attrs = link['attrs']
        classes = (attrs.get('class') or '').split()
        primary = attrs.get('id') == 'download_link' or 'download-start-btn' in classes
        if not primary:
            continue
        target = checked_url(urllib.parse.urljoin(final_url, attrs.get('href', '')))
        if not apkpure_host(urllib.parse.urlsplit(target).hostname or ''):
            continue
        # Exclude the store installer and other app IDs when the URL exposes one.
        match = re.search(r'/b/(?:APK|XAPK)/([^/?]+)', urllib.parse.urlsplit(target).path)
        if match and PACKAGE.fullmatch(match[1]) and match[1] != expected:
            continue
        downloads.setdefault(target, {'url': target, 'label': attrs.get('title') or link['text']})
    for link in page.links:
        target = urllib.parse.urljoin(final_url, link['attrs'].get('href', ''))
        if target in downloads:
            for key in ('version', 'version_code', 'file_size'):
                value = link['attrs'].get('data-dt-' + key)
                if value:
                    downloads[target][key] = value
    metadata = {}
    for value in page.structured:
        for item in json_objects(value):
            kind = item.get('@type')
            if kind not in ('MobileApplication', 'SoftwareApplication'):
                continue
            item_url = item.get('url') or item.get('@id', '')
            if not isinstance(item_url, str) or expected not in urllib.parse.urlsplit(item_url).path.split('/'):
                continue
            metadata = {key: item.get(key) for key in ('name', 'softwareVersion', 'publisher', 'operatingSystem', 'fileSize')}
            break
    hashes = sorted(set(re.findall(r'SHA[ -]?256\s*:\s*([a-fA-F0-9]{64})', ' '.join(page.text), re.I)))
    return {'status': 'resolved' if downloads else 'no_download_link', 'page_url': final_url,
            'package_id': expected, 'metadata': metadata, 'downloads': list(downloads.values()),
            'published_sha256_candidates': hashes,
            'limits': ['Page metadata is a source claim; inspect the downloaded Manifest and signatures.',
                       'A latest link can change between resolution and download; pin version/hash where available.',
                       'No JavaScript, cookies, authentication, or challenge solving is performed.']}


def validate_carrier(path, expected, max_unpacked, max_members):
    budget = {'bytes': 0, 'members': 0}
    abis = set()

    def inspect(archive):
        infos = archive.infolist()
        budget['bytes'] += sum(info.file_size for info in infos)
        budget['members'] += len(infos)
        if budget['bytes'] > max_unpacked or budget['members'] > max_members:
            raise AcquisitionError('Archive exceeds validation limits')
        names = [info.filename for info in infos]
        if len(set(names)) != len(names) or any(info.flag_bits & 1 for info in infos):
            raise AcquisitionError('Duplicate ZIP members or encrypted members are unsupported')
        bad = archive.testzip()
        if bad:
            raise AcquisitionError('ZIP CRC check failed')
        for name in names:
            pieces = name.split('/')
            if len(pieces) == 3 and pieces[0] == 'lib' and name.endswith('.so'):
                abis.add(pieces[1])
        return infos, names

    with zipfile.ZipFile(path) as archive:
        infos, names = inspect(archive)
        if 'AndroidManifest.xml' in names:
            if archive.getinfo('AndroidManifest.xml').file_size == 0:
                raise AcquisitionError('Empty Android Manifest')
            return {'format': 'apk', 'abis': sorted(abis), 'package_identity': 'requires_binary_manifest_check'}
        nested = [info for info in infos if info.filename.lower().endswith('.apk') and not info.is_dir()]
        if 'manifest.json' not in names or not nested or archive.getinfo('manifest.json').file_size > 1024**2:
            raise AcquisitionError('ZIP is not an APK or a recognized XAPK carrier')
        manifest = json.loads(archive.read('manifest.json'))
        if not isinstance(manifest, dict):
            raise AcquisitionError('XAPK manifest must be an object')
        declared = manifest.get('package_name')
        if expected and declared and declared != expected:
            raise AcquisitionError('XAPK declared package does not match the selected app')
        for info in nested:
            with tempfile.SpooledTemporaryFile(max_size=16 * 1024**2) as spool:
                with archive.open(info) as stream:
                    shutil.copyfileobj(stream, spool, 1024 * 1024)
                spool.seek(0)
                with zipfile.ZipFile(spool) as child:
                    _, child_names = inspect(child)
                    if 'AndroidManifest.xml' not in child_names or not child.getinfo('AndroidManifest.xml').file_size:
                        raise AcquisitionError('An XAPK member is not structurally an APK')
        return {'format': 'xapk', 'abis': sorted(abis), 'nested_apks': len(nested),
                'declared_package': declared, 'declared_version': manifest.get('version_name'),
                'package_identity': 'container_claim_only; verify_nested_binary_manifests'}


def fetch(args):
    destination = args.output_dir.expanduser().absolute()
    if destination.exists() or destination.is_symlink():
        raise AcquisitionError('Output directory must be a new path')
    destination.parent.mkdir(parents=True, exist_ok=True)
    started = time.monotonic()
    created = False
    with tempfile.TemporaryDirectory(prefix='.rea-gp-download-', dir=destination.parent) as staging:
        stage = Path(staging)
        temporary = stage / 'payload.part'
        digest, size = hashlib.sha256(), 0
        with open_url(args.url, args.timeout, args.source_page) as response:
            if response.headers.get_content_type() in ('text/html', 'application/xhtml+xml'):
                raise AcquisitionError('Received an HTML page instead of a package; resolve its download link first')
            length = response.headers.get('Content-Length')
            expected_size = int(length) if length is not None else None
            if expected_size is not None and (expected_size < 0 or expected_size > args.max_bytes):
                raise AcquisitionError('Declared download size exceeds the configured limit')
            final_url = checked_url(response.geturl())
            with temporary.open('xb') as stream:
                while True:
                    if time.monotonic() - started > args.deadline:
                        raise AcquisitionError('Download exceeded its time budget')
                    chunk = response.read(1024 * 1024)
                    if not chunk:
                        break
                    size += len(chunk)
                    if size > args.max_bytes:
                        raise AcquisitionError('Download exceeded its byte limit')
                    digest.update(chunk)
                    stream.write(chunk)
            if expected_size is not None and expected_size != size:
                raise AcquisitionError('Incomplete response: Content-Length mismatch')
        sha = digest.hexdigest()
        if args.sha256 and sha != args.sha256.lower():
            raise AcquisitionError('Downloaded SHA-256 does not match the expected value')
        carrier = validate_carrier(temporary, args.package_id, args.max_unpacked_bytes, args.max_members)
        filename = 'package.' + carrier['format']
        temporary.rename(stage / filename)
        record = {'status': 'downloaded', 'retrieved_at': datetime.now(timezone.utc).isoformat(),
                  'query': args.query, 'source_page': public_url(args.source_page) if args.source_page else None,
                  'requested_url': public_url(args.url), 'final_url': public_url(final_url),
                  'expected_package': args.package_id, 'expected_sha256': args.sha256,
                  'sha256': sha, 'bytes': size, 'artifact': str(destination / filename), 'carrier': carrier,
                  'limits': ['ZIP/CRC checks do not establish publisher identity or APK signature validity.',
                             'No installation, target execution, or resource extraction was performed.']}
        (stage / 'source.json').write_text(json.dumps(record, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
        try:
            destination.mkdir()  # Exclusive reservation: never overwrite an existing directory or symlink.
            created = True
            for item in stage.iterdir():
                item.rename(destination / item.name)
        except BaseException:
            if created:
                shutil.rmtree(destination)
            raise
    return record


def positive(value):
    result = float(value)
    if result <= 0 or not result < float('inf'):
        raise argparse.ArgumentTypeError('Value must be finite and positive')
    return result


def positive_int(value):
    result = int(value)
    if result <= 0:
        raise argparse.ArgumentTypeError('Value must be positive')
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest='command', required=True)
    find = commands.add_parser('search', help='List APKPure candidates for a game name; never auto-select')
    find.add_argument('query')
    find.add_argument('--limit', type=positive_int, default=10)
    page = commands.add_parser('resolve', help='Read observed target download links from an APKPure page')
    page.add_argument('url')
    download = commands.add_parser('fetch', help='Download an observed direct URL and validate it without execution')
    download.add_argument('url')
    download.add_argument('--output-dir', type=Path, required=True)
    download.add_argument('--source-page')
    download.add_argument('--query')
    download.add_argument('--package-id')
    download.add_argument('--sha256')
    download.add_argument('--max-bytes', type=positive_int, default=2 * 1024**3)
    download.add_argument('--max-unpacked-bytes', type=positive_int, default=8 * 1024**3)
    download.add_argument('--max-members', type=positive_int, default=100000)
    download.add_argument('--deadline', type=positive, default=600)
    for command in (find, page, download):
        command.add_argument('--timeout', type=positive, default=30)
    args = parser.parse_args()
    if args.command == 'fetch':
        if args.package_id and not PACKAGE.fullmatch(args.package_id):
            parser.error('--package-id must be an Android package identifier')
        if args.sha256 and not re.fullmatch(r'[a-fA-F0-9]{64}', args.sha256):
            parser.error('--sha256 must be a complete SHA-256')
        result = fetch(args)
    elif args.command == 'search':
        if not args.query.strip():
            parser.error('The search query must not be empty')
        result = search(args.query.strip(), args.timeout, args.limit)
    else:
        result = resolve(args.url, args.timeout)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result['status'] in ('candidates', 'resolved', 'downloaded') else 2


if __name__ == '__main__':
    try:
        sys_exit = main()
    except urllib.error.HTTPError as exc:
        print(json.dumps({'status': 'http_error', 'http_status': exc.code,
                          'message': 'Use an accessible public page or host browser; no authentication/challenge bypass is attempted.'}), file=sys.stderr)
        sys_exit = 1
    except (OSError, ValueError, RuntimeError, urllib.error.URLError, http.client.HTTPException, zipfile.BadZipFile) as exc:
        message = str(exc) if isinstance(exc, AcquisitionError) else 'Acquisition failed (' + type(exc).__name__ + '); no validated output was published'
        print(json.dumps({'status': 'error', 'message': message}), file=sys.stderr)
        sys_exit = 1
    raise SystemExit(sys_exit)
