#!/usr/bin/env python3
"""Inventory ZIP/APK/XAPK carriers without extraction to target paths or execution."""
import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
import shutil
import sys
import tempfile
import zipfile


def hash_stream(stream):
    h = hashlib.sha256()
    while chunk := stream.read(1024*1024):
        h.update(chunk)
    return h.hexdigest()


def member_record(info):
    return {'path':info.filename,'bytes':info.file_size,'compressed_bytes':info.compress_size,
            'compression':info.compress_type,'crc32':f'{info.CRC:08x}',
            'encrypted':bool(info.flag_bits & 1)}


def inspect(archive, all_members=False, hash_members=False):
    infos = archive.infolist()
    names = [i.filename for i in infos]
    counts = Counter(names)
    duplicates = [n for n, count in counts.items() if count > 1]
    dex = [n for n in names if n.lower().endswith('.dex')]
    native = [n for n in names if n.lower().endswith('.so')]
    metadata = [n for n in names if n.endswith('global-metadata.dat')]
    apks = [i for i in infos if i.filename.lower().endswith('.apk')]
    abis = sorted({n.split('/')[1] for n in native if n.startswith('lib/') and len(n.split('/')) == 3})
    selected = set(dex+native+metadata+[i.filename for i in apks]+['AndroidManifest.xml','manifest.json'])
    members = []
    for info in infos:
        if not all_members and info.filename not in selected:
            continue
        record = member_record(info)
        if hash_members and not info.is_dir():
            with archive.open(info) as stream:
                record['sha256'] = hash_stream(stream)
        members.append(record)
    manifest_format = None
    if counts['AndroidManifest.xml'] == 1:
        with archive.open('AndroidManifest.xml') as stream:
            header = stream.read(64)
        manifest_format = 'xml' if header.lstrip().startswith(b'<') else 'binary_axml_header' if header[:4] == b'\x03\x00\x08\x00' else 'unknown'
    return {'entries':len(infos), 'uncompressed_bytes':sum(i.file_size for i in infos),
            'duplicate_name_count':len(duplicates), 'duplicate_names':duplicates[:100],
            'abis':abis, 'dex_candidates':dex, 'native_candidates':native,
            'metadata_candidates':metadata, 'manifest_format':manifest_format,
            'packaged_signals':{'il2cpp_library':any(Path(n).name == 'libil2cpp.so' for n in native),
                                'managed_assemblies':any(n.lower().endswith('.dll') for n in names)},
            'asset_compression_counts':dict(Counter(str(i.compress_type) for i in infos if i.filename.startswith('assets/') and not i.is_dir())),
            'members':members}, apks


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('input', type=Path)
    parser.add_argument('--output', type=Path)
    parser.add_argument('--nested', action='store_true', help='Inspect one level of nested APKs')
    parser.add_argument('--all-members', action='store_true')
    parser.add_argument('--hash-members', action='store_true', help='Hash selected members; reads their contents')
    parser.add_argument('--max-nested-bytes', type=int, default=2*1024**3)
    args = parser.parse_args()
    if args.max_nested_bytes <= 0:
        parser.error('--max-nested-bytes must be positive')
    source = args.input.resolve()
    if args.output is not None and (args.output.is_symlink() or args.output.resolve() == source or args.output.exists()):
        raise ValueError('Output must be a new path, distinct from input')
    with source.open('rb') as stream:
        source_sha = hash_stream(stream)
    with zipfile.ZipFile(source) as archive:
        result, nested = inspect(archive, args.all_members, args.hash_members)
        result.update(source=str(source), source_sha256=source_sha, carrier_bytes=source.stat().st_size)
        if args.nested:
            result['nested_apks'] = []
            for info in nested:
                item = {'carrier_member':info.filename}
                if info.file_size > args.max_nested_bytes:
                    item.update(status='skipped',reason='Nested APK exceeds size limit',bytes=info.file_size)
                else:
                    # A spooled file bounds RAM; members are never published to archive paths.
                    with tempfile.SpooledTemporaryFile(max_size=16*1024**2) as spool:
                        with archive.open(info) as stream:
                            shutil.copyfileobj(stream, spool, 1024*1024)
                        spool.seek(0)
                        item['sha256'] = hash_stream(spool)
                        spool.seek(0)
                        try:
                            with zipfile.ZipFile(spool) as child:
                                item['inventory'], _ = inspect(child, args.all_members, args.hash_members)
                            item['status'] = 'inspected'
                        except zipfile.BadZipFile:
                            item.update(status='invalid_zip',reason='Member named APK is not a valid ZIP')
                result['nested_apks'].append(item)
    result['limits'] = ['Names and packaged signals do not establish runtime activation.',
                        'Binary Manifest, ELF layouts, signatures and target execution are not analyzed.',
                        'Nested inspection is one level only; skipped members remain explicit.']
    text = json.dumps(result, ensure_ascii=False, indent=2)+'\n'
    if args.output is not None:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        with args.output.open('x', encoding='utf-8') as stream:
            stream.write(text)
        print(json.dumps({'output':str(args.output.absolute()),'source_sha256':source_sha,'entries':result['entries']}))
    else:
        print(text, end='')


if __name__ == '__main__':
    try:
        main()
    except (OSError, ValueError, RuntimeError, zipfile.BadZipFile) as exc:
        print(json.dumps({'status':'error','message':str(exc)}), file=sys.stderr)
        sys.exit(1)
