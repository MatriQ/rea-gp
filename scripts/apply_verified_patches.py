#!/usr/bin/env python3
"""Apply source-bound, equal-length byte patches to a new file; no target execution."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import stat
import struct
import sys
import tempfile


def number(value):
    if isinstance(value, bool) or not isinstance(value, (int, str)):
        raise ValueError('Address must be an integer or an integer string')
    result = int(value, 0) if isinstance(value, str) else value
    if result < 0:
        raise ValueError('Negative address')
    return result


def digest(raw):
    return hashlib.sha256(raw).hexdigest()


def sha_field(value):
    if not isinstance(value, str) or not re.fullmatch(r'[0-9a-fA-F]{64}', value):
        raise ValueError('Expected a complete SHA-256 hex digest')
    return value.lower()


def elf_offset(raw, address, length):
    if len(raw) < 16 or raw[:4] != b'\x7fELF' or raw[4] not in (1, 2) or raw[5] not in (1, 2):
        raise ValueError('virtual_address requires an ELF32 or ELF64 input')
    elf64 = raw[4] == 2
    endian = '<' if raw[5] == 1 else '>'
    if len(raw) < (64 if elf64 else 52):
        raise ValueError('Truncated ELF header')
    phoff = struct.unpack_from(endian+('Q' if elf64 else 'I'), raw, 32 if elf64 else 28)[0]
    size, count = struct.unpack_from(endian+'HH', raw, 54 if elf64 else 42)
    if size < (56 if elf64 else 32) or phoff + size * count > len(raw):
        raise ValueError('Invalid ELF program header table')
    matches = []
    for i in range(count):
        if elf64:
            typ, _, off, va, _, filesz, memsz, _ = struct.unpack_from(endian+'II6Q', raw, phoff+i*size)
        else:
            typ, off, va, _, filesz, memsz, _, _ = struct.unpack_from(endian+'8I', raw, phoff+i*size)
        if typ != 1:
            continue
        if filesz > memsz or off + filesz > len(raw):
            raise ValueError('Invalid ELF load segment')
        if va <= address and address + length <= va + filesz:
            matches.append(off + address - va)
    if len(matches) != 1:
        raise ValueError('VA patch must map wholly into one file-backed PT_LOAD')
    return matches[0]


def prepare(raw, plan):
    if not isinstance(plan, dict):
        raise ValueError('Plan must be a JSON object')
    if digest(raw) != sha_field(plan['input_sha256']):
        raise ValueError('Input SHA-256 mismatch; wrong version or recovery stage')
    patches = plan['patches']
    if not isinstance(patches, list) or not patches:
        raise ValueError('patches must be a nonempty array')
    checked = []
    for index, patch in enumerate(patches):
        if not isinstance(patch, dict):
            raise ValueError('Each patch must be a JSON object')
        before, after = bytes.fromhex(patch['before']), bytes.fromhex(patch['after'])
        if not before or len(before) != len(after):
            raise ValueError('Patch must have nonempty, equal-length before/after bytes')
        mapped = elf_offset(raw, number(patch['virtual_address']), len(before)) if 'virtual_address' in patch else None
        offset = number(patch['file_offset']) if 'file_offset' in patch else mapped
        if offset is None:
            raise ValueError('Patch requires file_offset or virtual_address')
        if mapped is not None and mapped != offset:
            raise ValueError('VA and file offset disagree')
        if offset + len(before) > len(raw) or raw[offset:offset+len(before)] != before:
            raise ValueError('Patch preimage mismatch at '+hex(offset))
        checked.append((offset, before, after, patch.get('name', str(index))))
    ordered = sorted(checked, key=lambda item: item[0])
    for left, right in zip(ordered, ordered[1:]):
        if left[0] + len(left[1]) > right[0]:
            raise ValueError('Overlapping patches')
    result = bytearray(raw)
    for offset, before, after, _ in checked:
        result[offset:offset+len(before)] = after
    out_sha = digest(result)
    if 'output_sha256' in plan and out_sha != sha_field(plan['output_sha256']):
        raise ValueError('Output SHA-256 mismatch')
    return result, checked, out_sha


def write_new(destination, raw, mode):
    destination.parent.mkdir(parents=True, exist_ok=True)
    temporary = None
    try:
        with tempfile.NamedTemporaryFile(dir=destination.parent, prefix='.rea-gp-', delete=False) as f:
            temporary = Path(f.name)
            if hasattr(os, 'fchmod'):
                os.fchmod(f.fileno(), mode)
            else:
                os.chmod(f.name, mode)
            f.write(raw)
            f.flush()
            os.fsync(f.fileno())
        # Hard-link publication is atomic and refuses to overwrite an existing file.
        os.link(temporary, destination)
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('plan', type=Path)
    parser.add_argument('--input', required=True, type=Path)
    parser.add_argument('--output', type=Path)
    parser.add_argument('--dry-run', action='store_true')
    args = parser.parse_args()
    if not args.dry_run and args.output is None:
        parser.error('--output is required unless --dry-run is used')
    source = args.input.resolve()
    if args.output is not None and args.output.is_symlink():
        raise ValueError('Output must not be an existing symlink')
    destination = args.output.resolve() if args.output is not None else None
    if destination is not None and (destination == source or destination.exists()):
        raise ValueError('Output must be a new path, distinct from input')
    raw = source.read_bytes()
    plan = json.loads(args.plan.read_text(encoding='utf-8'))
    result, patches, output_sha = prepare(raw, plan)
    if not args.dry_run:
        write_new(destination, result, stat.S_IMODE(source.stat().st_mode))
    print(json.dumps({'status':'patches_verified', 'dry_run':args.dry_run,
                     'input':str(source), 'input_sha256':digest(raw),
                     'output':None if args.dry_run else str(destination),
                     'output_sha256':output_sha, 'patch_count':len(patches),
                     'patches':[{'name':n,'file_offset':hex(o),'before':b.hex(),'after':a.hex()}
                                for o,b,a,n in patches]}, indent=2))


if __name__ == '__main__':
    try:
        main()
    except (OSError, ValueError, KeyError, TypeError, struct.error) as exc:
        print(json.dumps({'status':'error','message':str(exc)}), file=sys.stderr)
        sys.exit(1)
