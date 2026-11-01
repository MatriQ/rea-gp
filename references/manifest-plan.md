# Exact Manifest edit plans

`scripts/patch_manifest.py` edits **text XML** decoded by tools such as apktool. It verifies the input text's SHA-256, applies explicitly selected node/metadata changes, and writes a new file. It does not edit binary Manifests inside APKs, select SDKs to disable, or implement async callback replacements.

## Plan fields

| Field | Format and behavior |
| --- | --- |
| `input_sha256` | Required full SHA-256 of the input text XML. |
| `remove_components` | Array. Each item's `tag` is provider/service/receiver/activity/activity-alias; `name` exactly matches android:name on a direct application child. `expected_count` defaults to 1. |
| `remove_permissions` | Array. Each item supplies literal `name`, optional `tag` (uses-permission or uses-permission-sdk-23), and `expected_count`. Matches direct manifest children only. |
| `remove_metadata` | Array. Each item has `name` and optional `expected_count`; by default matches only direct application meta-data. For a registrar inside a component, also supply `parent_tag` and exact `parent_name`; the parent must be unique. |
| `set_metadata` | Object keyed by android:name of direct application metadata, with boolean, finite numeric, or string values. Sets android:value and explicitly replaces existing android:resource. Duplicate same-name nodes fail. |
| `remove_root_attributes` | String array. Supports only `android:`-qualified or unqualified manifest root attributes. Missing attributes fail. |
| `notes` | Optional explanatory data. Other unknown fields are rejected to prevent silent omissions from typos. |

Names match literal values stored in the decoded XML. Fully qualified names and `.RelativeName` are not automatically equivalent. Selectors do not expand into package-prefix or regex deletion. Incorrect counts, duplicate nodes, wrong hashes, or existing outputs fail without publishing partial edits.

## Usage

1. Analyze actual entry points and shared consumers, then generate a task plan containing selected operations.
2. Run `--dry-run` first and inspect names, expected counts, and change records.
3. Generate independent XML with `--output` and use it in a build-source copy, preserving the original decoded tree.
4. Structurally compare unselected components, attributes, permissions, intent filters, child metadata, and order.
5. Rebuild with apktool/aapt2 and reparse the binary Manifest. Verify corresponding Java/JNI calls and task completion as well; node deletion alone does not prove an SDK is disabled.

```bash
python3 scripts/patch_manifest.py MANIFEST_PLAN_JSON --input DECODED_MANIFEST_XML --dry-run
python3 scripts/patch_manifest.py MANIFEST_PLAN_JSON --input DECODED_MANIFEST_XML --output NEW_MANIFEST_XML
```

Metadata values are configuration. Retained code may explicitly initialize again or override them. Handle those calls within the selected [Firebase](firebase.md), [ads](ads.md), or [resources](resources-and-downloads.md) module.
