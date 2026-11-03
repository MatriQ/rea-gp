"""Acquisition contract tests using isolated HTML and a local HTTP server."""
import argparse
import hashlib
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import io
import json
from pathlib import Path
import sys
import tempfile
import threading
import unittest
from unittest.mock import patch
import urllib.error
import zipfile

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
import acquire_package as acquire


def archive(entries):
    output = io.BytesIO()
    with zipfile.ZipFile(output, 'w', compression=zipfile.ZIP_STORED) as stream:
        for name, value in entries.items():
            stream.writestr(name, value)
    return output.getvalue()


APK = archive({'AndroidManifest.xml': b'\x03\x00\x08\x00sample', 'lib/arm64-v8a/libsample.so': b'sample'})
XAPK = archive({'manifest.json': json.dumps({'package_name': 'org.example.game', 'version_name': '1.2'}),
                'base.apk': APK})
PAGE_URL = 'https://apkpure.net/sample/org.example.game/download'


class Parsing(unittest.TestCase):
    def page(self, text):
        page = acquire.Page()
        page.feed(text)
        return page

    def test_search_preserves_ambiguous_names_and_excludes_unscoped_ad_links(self):
        page = self.page('''
          <a href="/store/org.example.installer" title="Install Store">Store</a>
          <a data-dt-pkg="org.example.game" href="/sample/org.example.game" title="Sample Puzzle">Sample Puzzle Example Studio</a>
          <a data-dt-pkg="org.example.clone" href="/clone/org.example.clone" title="Sample Puzzle">Sample Puzzle Other Studio</a>
          <a data-dt-pkg="org.example.game" href="/sample/org.example.game">Duplicate</a>
          <a data-dt-pkg="org.example.wrong" href="/sample/org.example.different">Mismatch</a>
        ''')
        with patch.object(acquire, 'read_page', return_value=(page, 'https://apkpure.net/search?q=sample')):
            result = acquire.search('Sample Puzzle', 1, 10)
        self.assertEqual([item['package_id'] for item in result['candidates']], ['org.example.game', 'org.example.clone'])
        self.assertIn('Example Studio', result['candidates'][0]['listing_text'])

    def test_resolve_selects_target_links_and_keeps_version_evidence(self):
        digest = 'a' * 64
        page = self.page('''
          <a id="download_link" href="https://d.apkpure.net/b/XAPK/org.example.game?version=latest">Click here</a>
          <a class="download-start-btn" href="https://d.apkpure.net/b/XAPK/org.example.game?version=latest">Download XAPK</a>
          <a data-dt-version="1.2" data-dt-version_code="12" data-dt-file_size="4000"
             href="https://d.apkpure.net/b/XAPK/org.example.game?version=latest">Download</a>
          <a class="aegon-download-link" href="https://d.apkpure.net/store.apk">Install Store</a>
          <a id="download_link" href="https://d.apkpure.net/b/APK/org.example.installer?version=latest">Wrong app</a>
          <script type="application/ld+json">{"@type":"MobileApplication","url":"https://apkpure.net/sample/org.example.game",
            "name":"Sample Puzzle","publisher":{"name":"Example Studio"},"softwareVersion":"1.2"}</script>
        ''' + '<div>SHA-256: ' + digest + '</div>')
        with patch.object(acquire, 'read_page', return_value=(page, PAGE_URL)):
            result = acquire.resolve(PAGE_URL, 1)
        self.assertEqual(result['status'], 'resolved')
        self.assertEqual(len(result['downloads']), 1)
        self.assertEqual(result['downloads'][0]['version'], '1.2')
        self.assertEqual(result['metadata']['publisher']['name'], 'Example Studio')
        self.assertEqual(result['published_sha256_candidates'], [digest])

    def test_changed_page_identity_is_rejected(self):
        with patch.object(acquire, 'read_page', return_value=(self.page(''), 'https://apkpure.net/other/org.example.other/download')):
            with self.assertRaises(acquire.AcquisitionError):
                acquire.resolve(PAGE_URL, 1)

    def test_no_link_is_explicit_and_urls_cannot_load_local_files(self):
        with patch.object(acquire, 'read_page', return_value=(self.page('<h1>Challenge</h1>'), PAGE_URL)):
            self.assertEqual(acquire.resolve(PAGE_URL, 1)['status'], 'no_download_link')
        for value in ('file:///etc/passwd', 'https://user:password@example.com/file'):
            with self.subTest(value=value), self.assertRaises(acquire.AcquisitionError):
                acquire.checked_url(value)


class Handler(BaseHTTPRequestHandler):
    def log_message(self, *args):
        pass

    def do_GET(self):
        name = self.path.split('?', 1)[0]
        if name in ('/redirect', '/loop'):
            self.send_response(302)
            self.send_header('Location', '/apk' if name == '/redirect' else '/loop')
            self.end_headers()
            return
        payload = XAPK if name == '/xapk' else b'<html>challenge</html>' if name == '/html' else APK
        self.send_response(200)
        self.send_header('Content-Type', 'text/html' if name == '/html' else 'application/octet-stream')
        self.send_header('Content-Length', str(len(payload) + (10 if name == '/short' else 0)))
        self.end_headers()
        self.wfile.write(payload)


class Downloading(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.server = ThreadingHTTPServer(('127.0.0.1', 0), Handler)
        cls.thread = threading.Thread(target=cls.server.serve_forever, daemon=True)
        cls.thread.start()
        cls.base = 'http://127.0.0.1:' + str(cls.server.server_port)

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()
        cls.thread.join()

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='rea-gp-test-')
        self.addCleanup(self.temp.cleanup)
        self.destination = Path(self.temp.name) / 'new download'

    def args(self, path='/apk', **changes):
        options = dict(url=self.base + path, output_dir=self.destination,
                       source_page=self.base + '/source?credential=secret', query='Sample Puzzle',
                       package_id='org.example.game', sha256=None, max_bytes=100000,
                       max_unpacked_bytes=100000, max_members=100, timeout=2, deadline=10)
        options.update(changes)
        return argparse.Namespace(**options)

    def assert_no_output(self):
        self.assertFalse(self.destination.exists())
        self.assertEqual(list(Path(self.temp.name).iterdir()), [])

    def test_apk_is_hashed_and_provenance_redacts_query_credentials(self):
        result = acquire.fetch(self.args('/apk?credential=secret'))
        self.assertEqual((self.destination / 'package.apk').read_bytes(), APK)
        self.assertEqual(result['sha256'], hashlib.sha256(APK).hexdigest())
        self.assertEqual(result['carrier']['abis'], ['arm64-v8a'])
        self.assertNotIn('secret', (self.destination / 'source.json').read_text())
        self.assertIn('requires_binary_manifest_check', result['carrier']['package_identity'])

    def test_xapk_keeps_all_splits_and_declared_identity_separate(self):
        result = acquire.fetch(self.args('/xapk'))
        self.assertEqual((self.destination / 'package.xapk').read_bytes(), XAPK)
        self.assertEqual(result['carrier']['nested_apks'], 1)
        self.assertEqual(result['carrier']['declared_package'], 'org.example.game')

    def test_observed_redirect_is_recorded(self):
        result = acquire.fetch(self.args('/redirect'))
        self.assertEqual(result['final_url'], self.base + '/apk')

    def test_wrong_hash_does_not_publish_or_leave_partial_download(self):
        with self.assertRaises(acquire.AcquisitionError):
            acquire.fetch(self.args(sha256='0' * 64))
        self.assert_no_output()

    def test_html_and_truncated_responses_are_not_packages(self):
        for path in ('/html', '/short'):
            with self.subTest(path=path), self.assertRaises(acquire.AcquisitionError):
                acquire.fetch(self.args(path))
            self.assert_no_output()

    def test_size_archive_and_member_limits(self):
        for change in ({'max_bytes': 1}, {'max_unpacked_bytes': 1}, {'max_members': 1}):
            with self.subTest(change=change), self.assertRaises(acquire.AcquisitionError):
                acquire.fetch(self.args(**change))
            self.assert_no_output()

    def test_existing_output_is_preserved(self):
        self.destination.mkdir()
        marker = self.destination / 'keep.txt'
        marker.write_text('keep')
        with self.assertRaises(acquire.AcquisitionError):
            acquire.fetch(self.args())
        self.assertEqual(marker.read_text(), 'keep')

    def test_declared_package_mismatch_does_not_publish(self):
        with self.assertRaises(acquire.AcquisitionError):
            acquire.fetch(self.args('/xapk', package_id='org.example.other'))
        self.assert_no_output()

    def test_redirect_loop_is_bounded(self):
        with self.assertRaises(urllib.error.HTTPError):
            acquire.fetch(self.args('/loop'))
        self.assert_no_output()

    def test_crc_failure_and_non_package_archives_are_rejected(self):
        path = Path(self.temp.name) / 'sample.zip'
        corrupt = APK.replace(b'sample', b'broken', 1)
        for payload in (corrupt, archive({'readme.txt': 'not an Android package'})):
            path.write_bytes(payload)
            with self.subTest(payload=len(payload)), self.assertRaises((acquire.AcquisitionError, zipfile.BadZipFile)):
                acquire.validate_carrier(path, None, 100000, 100)


if __name__ == '__main__':
    unittest.main()
