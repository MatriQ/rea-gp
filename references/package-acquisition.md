# Obtain a game package from its name

Use this route when the user provides a game name, store page, or download URL instead of a local package. Reuse a suitable local artifact when one already exists. Package acquisition prepares the requested analysis/modification task; installation and game changes remain governed by the user's scope.

## Identify the intended game

1. Reuse the conversation's title, publisher, package ID, version, region, and device requirements. A Chinese title may need an English/localized alias; retain the original query in the task record.
2. Search the publisher's actual release channel or the user's preferred source. APKPure is a supported public source. Its current pages are available through [APKPure](https://apkpure.net/); verify actual domains and links rather than trusting similarly named sites.
3. Compare title **and** developer/package identity. Distinguish sequels, regional editions, demos, and modified builds. A result's position or download count is not an identity check.
4. Continue automatically for an established match. When multiple plausible identities remain, show a short list with publisher/package differences and ask the one question needed to choose. Continue independent tool setup while waiting; do not download every candidate.
5. Honor a requested version/ABI. Otherwise use the latest stable compatible version visibly offered by the chosen source and record that choice. Inspect variants when the known target device requires them. Do not connect a device solely to resolve a download unless device work is already in scope.

## Search, resolve, fetch

The bundled helper uses Python's standard library and does not depend on an agent vendor. It has three separate stages so the agent can make identity and variant decisions between requests:

```bash
python3 scripts/acquire_package.py search "GAME_NAME" --limit 10
python3 scripts/acquire_package.py resolve APP_DOWNLOAD_PAGE_URL
python3 scripts/acquire_package.py fetch OBSERVED_DOWNLOAD_URL --source-page APP_DOWNLOAD_PAGE_URL --query "GAME_NAME" --package-id PACKAGE_ID --output-dir NEW_DOWNLOAD_DIRECTORY
```

Resolve script paths from the skill root. Store downloads in the task workspace, outside the skill repository.

- **Search:** Queries APKPure's public search page and returns structured app-card candidates with title, package ID, listing text, and page URL. Listing text can supply developer clues; verify the publisher on the selected app page. The helper never automatically selects the first candidate.
- **Resolve:** Read the selected version/download page reached through the site's actual download controls. The helper collects observed primary download links and available version/size/publisher metadata. It excludes unrelated installer/promotional controls. An app overview may need its download link followed before resolution. It does not invent CDN addresses or undocumented API requests.
- **Fetch:** Download one observed direct HTTP(S) URL, follow bounded redirects, hash it, validate the carrier, and write `package.apk` or `package.xapk` plus `source.json` to a **new** directory. Official publisher or other selected-source direct URLs also work with `fetch`.

Add `--sha256 EXPECTED_SHA256` when the chosen source publishes the **file** hash for that exact version/variant or a trusted prior artifact supplies it. A certificate fingerprint is not a file digest. Keep source hash claims distinct from hashes independently computed over downloaded bytes.

The agent orchestrates these stages automatically once identity and version are established. Follow the resulting local path into inventory and the requested REA_GP workflow; do not stop after returning a download link when acquisition was requested.

### Versions and changing pages

A URL containing `version=latest` can change between resolving and fetching. Prefer a visibly offered fixed-version link, and pin the expected file hash when available. Compare the downloaded version/package afterward. If the source changed, resolve again once and state the version obtained; do not silently label it as the earlier version.

JSON-LD, card attributes, and download controls are source adapters, not permanent API contracts. If structured results disappear, use the host's web search/browser to inspect the current public page and obtain the actual target link. Do not broaden selectors until they also accept unrelated recommendations or store installers. Update parser fixtures when changing the adapter.

For localized names, missing results, or an inaccessible search page, use queries such as the exact title plus publisher, `site:apkpure.net`, and a known package ID. Prefer page evidence over a search snippet's version or file size.

### Access and download limits

The helper performs no JavaScript execution, cookie import, login, CAPTCHA solving, or access-control bypass. For HTTP 403/429, a challenge, or a dynamically generated link, use an available host browser through its normal public flow. If user action/login is actually needed, request that specific action and continue independent work. If the source is unavailable, use another suitable public release source or accept a user-supplied file; report the source change. Do not manufacture a completed download or retry the same blocked request indefinitely.

Default fetch limits are 2 GiB downloaded bytes, 8 GiB aggregate declared uncompressed bytes across the carrier and nested APKs, 100,000 aggregate ZIP members, a 30-second network-operation timeout, and a 600-second download time budget. Adjust the explicit `--max-bytes`, `--max-unpacked-bytes`, `--max-members`, `--timeout`, and `--deadline` options for a justified target. Check disk space for large carriers and temporary validation copies. Fetch does not resume partial files; failed attempts clean their own staging directory.

## Verify the package before analysis

The helper rejects HTML responses, truncated declared lengths, mismatched expected hashes, invalid ZIP/CRC data, encrypted or duplicate members, and unsupported carriers. XAPK validation checks its manifest declaration and every nested APK's archive structure without extracting members to archive-supplied paths. Existing destinations are preserved.

These checks establish transfer/archive properties. They do not prove the publisher, binary Manifest identity, valid signatures, or compatibility. Before treating the download as the selected game:

1. Run `inventory_package.py DOWNLOADED_PACKAGE --nested --output NEW_INVENTORY_JSON` and retain the original carrier hash.
2. Inspect the actual base and split Manifests with aapt2/apktool. Verify package ID, version/code, minimum SDK, split relationships, and ABI against the selected candidate. The XAPK JSON declaration is only a source claim.
3. Use `apksigner verify --verbose --print-certs` on the APKs as appropriate. Compare certificates across the split set and against an established publisher/original-artifact identity when available. A download site's security badge is not that comparison.
4. Keep XAPK/ABI/resource splits intact. XAPK can include additional resources and multiple APKs; [APKPure's format guide](https://apkpure.net/how-to/how-to-install-xapk-apk) describes this distinction. Renaming an XAPK to `.apk` does not create an installable single APK. Merge only under the separate build workflow after verifying content/access requirements.
5. If identity, version, or ABI disagrees, resolve the selection before modifying or installing. Do not discard resource splits merely to make the extension match the user's wording.

`source.json` records the original query, source page, requested/final URL, actual retrieval time, byte count, SHA-256, expected package/hash, and carrier observations. Query parameters other than public search/version fields are redacted in this persisted record. Treat resolved signed URLs as temporary transport details and do not commit access tokens, cookies, packages, or task records to the skill repository.

Report which claims were confirmed through downloaded Manifests/signatures and which remain source metadata. Downloading a package does not establish that it was installed or executed.

## Validate adapter changes

```bash
python3 -m unittest discover -s tests -v
```

Tests use controlled HTML and a local HTTP server for ambiguous names, promotional links, redirects, transfer failures, ZIP integrity, output preservation, and provenance. A live search/resolve/fetch check should use one small publicly offered package in an isolated temporary directory, without installation. Report any live source restrictions separately from fixture results.
