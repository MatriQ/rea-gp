#!/usr/bin/env python3
"""Apply exact, source-bound edits to a decoded text AndroidManifest.xml."""
import argparse
import hashlib
import io
import json
import math
from pathlib import Path
import stat
import sys
import xml.etree.ElementTree as ET

sys.dont_write_bytecode = True
from apply_verified_patches import sha_field, write_new

ANDROID = 'http://schemas.android.com/apk/res/android'
A = '{'+ANDROID+'}'
COMPONENTS = {'provider', 'service', 'receiver', 'activity', 'activity-alias'}
OPERATIONS = {'remove_components', 'remove_permissions', 'remove_metadata',
              'set_metadata', 'remove_root_attributes'}


def digest(raw):
    return hashlib.sha256(raw).hexdigest()


def structural(element):
    tag = element.tag if isinstance(element.tag, str) else '#comment'
    text = element.text if element.text and element.text.strip() else ''
    return [tag, sorted(element.attrib.items()), text, [structural(c) for c in element]]


def node_hash(element):
    return digest(json.dumps(structural(element), ensure_ascii=False).encode('utf-8'))


def remove_exact(parent, tag, name, expected):
    if not isinstance(name, str) or not name or type(expected) is not int or expected < 1:
        raise ValueError('Removal needs a nonempty literal name and positive expected_count')
    matches = [c for c in parent if c.tag == tag and c.get(A+'name') == name]
    if len(matches) != expected:
        raise ValueError(f'Expected {expected} direct {tag} nodes named {name}; found {len(matches)}')
    hashes = [node_hash(c) for c in matches]
    for c in matches:
        parent.remove(c)
    return {'operation':'remove', 'tag':tag, 'name':name, 'count':len(matches), 'node_sha256':hashes}


def metadata_value(value):
    if isinstance(value, bool):
        return 'true' if value else 'false'
    if isinstance(value, str) or type(value) is int or (isinstance(value, float) and math.isfinite(value)):
        return str(value)
    raise ValueError('Metadata values must be finite numbers, booleans or strings')


def prepare(raw, plan):
    if not isinstance(plan, dict):
        raise ValueError('Plan must be a JSON object')
    unknown = set(plan)-OPERATIONS-{'input_sha256', 'notes'}
    if unknown:
        raise ValueError('Unknown plan fields: '+', '.join(sorted(unknown)))
    if digest(raw) != sha_field(plan['input_sha256']):
        raise ValueError('Manifest input SHA-256 mismatch')
    for operation in OPERATIONS-{'set_metadata'}:
        value = plan.get(operation, [])
        if not isinstance(value, list):
            raise ValueError(operation+' must be an array')
        if operation != 'remove_root_attributes' and any(not isinstance(s, dict) for s in value):
            raise ValueError(operation+' selectors must be objects')
    allowed_selectors = {
        'remove_components': {'tag', 'name', 'expected_count'},
        'remove_permissions': {'tag', 'name', 'expected_count'},
        'remove_metadata': {'name', 'expected_count', 'parent_tag', 'parent_name'}}
    for operation, allowed in allowed_selectors.items():
        for selector in plan.get(operation, []):
            if set(selector)-allowed:
                raise ValueError('Unknown selector fields in '+operation)
    for _, (prefix, uri) in ET.iterparse(io.BytesIO(raw), events=['start-ns']):
        if prefix and prefix.startswith('ns') and prefix[2:].isdigit():
            continue
        ET.register_namespace(prefix, uri)
    ET.register_namespace('android', ANDROID)
    parser = ET.XMLParser(target=ET.TreeBuilder(insert_comments=True))
    root = ET.fromstring(raw, parser=parser)
    apps = root.findall('application')
    if root.tag != 'manifest' or len(apps) != 1:
        raise ValueError('Expected one application in a decoded text manifest')
    app, changes = apps[0], []
    for selector in plan.get('remove_components', []):
        tag = selector['tag']
        if tag not in COMPONENTS:
            raise ValueError('Unsupported application component tag: '+str(tag))
        changes.append(remove_exact(app, tag, selector['name'], selector.get('expected_count', 1)))
    for selector in plan.get('remove_permissions', []):
        tag = selector.get('tag', 'uses-permission')
        if tag not in {'uses-permission', 'uses-permission-sdk-23'}:
            raise ValueError('Unsupported permission tag')
        changes.append(remove_exact(root, tag, selector['name'], selector.get('expected_count', 1)))
    for selector in plan.get('remove_metadata', []):
        parent = app
        if 'parent_tag' in selector or 'parent_name' in selector:
            if selector.get('parent_tag') not in COMPONENTS or not isinstance(selector.get('parent_name'), str) or not selector['parent_name']:
                raise ValueError('Nested metadata requires a component parent_tag and literal parent_name')
            parents = [c for c in app if c.tag == selector['parent_tag'] and c.get(A+'name') == selector.get('parent_name')]
            if len(parents) != 1:
                raise ValueError('Nested metadata parent must match exactly one component')
            parent = parents[0]
        changes.append(remove_exact(parent, 'meta-data', selector['name'], selector.get('expected_count', 1)))
    settings = plan.get('set_metadata', {})
    if not isinstance(settings, dict):
        raise ValueError('set_metadata must be an object')
    for name, value in settings.items():
        if not isinstance(name, str) or not name:
            raise ValueError('Metadata name must be nonempty')
        matches = [c for c in app if c.tag == 'meta-data' and c.get(A+'name') == name]
        if len(matches) > 1:
            raise ValueError('Duplicate application metadata: '+name)
        node = matches[0] if matches else ET.SubElement(app, 'meta-data', {A+'name':name})
        before = node_hash(node) if matches else None
        node.attrib.pop(A+'resource', None)
        node.set(A+'value', metadata_value(value))
        changes.append({'operation':'set_application_metadata','name':name,'old_node_sha256':before,'new_node_sha256':node_hash(node)})
    for name in plan.get('remove_root_attributes', []):
        if not isinstance(name, str) or not name:
            raise ValueError('Root attribute must be a nonempty string')
        if ':' in name and not name.startswith('android:'):
            raise ValueError('Only android: or unqualified root attributes are supported')
        key = A+name.split(':', 1)[1] if name.startswith('android:') else name
        if key not in root.attrib:
            raise ValueError('Root attribute not present: '+name)
        del root.attrib[key]
        changes.append({'operation':'remove_root_attribute','name':name})
    if not changes:
        raise ValueError('Plan has no operations')
    if hasattr(ET, 'indent'):
        ET.indent(root)
    result = ET.tostring(root, encoding='utf-8', xml_declaration=True)
    reparsed = ET.fromstring(result, parser=ET.XMLParser(target=ET.TreeBuilder(insert_comments=True)))
    if structural(root) != structural(reparsed):
        raise ValueError('XML serialization changed the planned structure')
    return result, changes


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('plan', type=Path)
    parser.add_argument('--input', type=Path, required=True)
    parser.add_argument('--output', type=Path)
    parser.add_argument('--dry-run', action='store_true')
    args = parser.parse_args()
    if not args.dry_run and args.output is None:
        parser.error('--output is required unless --dry-run is used')
    source = args.input.resolve()
    if args.output is not None and (args.output.is_symlink() or args.output.exists() or args.output.resolve() == source):
        raise ValueError('Output must be a new path, distinct from input')
    raw = source.read_bytes()
    result, changes = prepare(raw, json.loads(args.plan.read_text(encoding='utf-8')))
    destination = args.output.resolve() if args.output is not None else None
    if not args.dry_run:
        write_new(destination, result, stat.S_IMODE(source.stat().st_mode))
    print(json.dumps({'status':'manifest_plan_verified','dry_run':args.dry_run,
                     'input_sha256':digest(raw),'output_sha256':digest(result),
                     'output':None if args.dry_run else str(destination),'changes':changes},indent=2))


if __name__ == '__main__':
    try:
        main()
    except (OSError, ValueError, KeyError, TypeError, ET.ParseError) as exc:
        print(json.dumps({'status':'error','message':str(exc)}),file=sys.stderr)
        sys.exit(1)
