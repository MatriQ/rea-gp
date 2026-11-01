# Optional module: resource downloads and offline content

## Select a treatment

| Mode | Implementation boundary |
| --- | --- |
| Preserve | Retain the game's CDN, patches, events, and ordinary downloads; change only selected platform delivery entry points. |
| Merge available resources | Merge obtained, version-matched install-time packs/caches at equivalent resource paths, verifying integrity and access method. |
| Obtain selected resources, then make offline | Retrieve selected content from an established dependency list, create a verifiable local index, and adapt loading routes. |
| User-specified mirror | Adapt actual download requests, paths, manifests, and validation rules. Mirroring static resources does not reconstruct the game's business backend. |
| Locally available content only | Preserve truthful coverage and provide terminating states/UI handling for missing content; do not falsely report it downloaded or unlocked. |

Establish the content set before choices that affect storage, bandwidth, startup, or coverage. Removing Google Play alone preserves ordinary CDN downloads by default; PAD content needs a compatible delivery choice.

## Prove coverage from payloads and loaders

1. Inventory packages/caches by logical key, actual object type, source, version, ABI/platform, compression, size, hash, dependencies, and download state.
2. Use UnityPy, AssetRipper, or compatible tools to inspect AssetBundle/SerializedFile mappings through ResourceManager/container entries. Count level data, scenes, art, audio, atlases, and event configuration separately.
3. Validate actual TextAsset/FlatBuffers/JSON structure, key fields, numbering, and continuity. Numeric filenames do not prove level data; a chapter-named file may only be an atlas.
4. Trace actual consumers: key-based loading, local/remote thresholds, version switches, bundle routes, and missing-content fallbacks. A configuration declaration does not prove its content ships in the package.
5. Report logical level-data completeness, region/scene payload completeness, events, and first-start dependencies separately. A derived implementation may override the default local loader, or its method may always fail; verify actual configuration and method bodies.

Extract resources only into new directories and exclude unrelated credentials. Embedded service accounts/private keys do not automatically authorize remote administration or bulk export. Bound downloads by the user's request and available authorized access.

## Downloads, local caches, and mirrors

- Reconstruct the current request manifest and dependency graph before selecting content. Preserve URL path/case, versions, compression/encryption, CRC/hash, ETag, dependency order, and local naming. URL strings are clues that must match actual download calls.
- Retrieve selected content into the task directory with curl/httpx or the actual downloader, using an existing authorized access context without exposing tokens. Register files and validation results in the task resource inventory. Do not default to enumerating an unrelated CDN prefix.
- Reuse the original temporary-file, integrity-check, atomic-move, load, cache-index, and completion chain. Enter success only after file/content verification. Failure and cancellation must also terminate waits.
- Prefer a loading provider/factory or verified path route for local replacement. Changing `IsDownloaded`/`IsAvailable` alone does not provide loadable content.
- Preserve resource identity and validation semantics when mirroring. Analyze business login, configuration, cloud saves, and payment services separately. For signed manifests/server authorization, state compatibility limits instead of assuming a domain change completes the protocol.

## Merge APKs and remove PAD

Check same-path entries, conflicts, and platform compatibility across the base and every pack. Preserve ZIP_STORED access needed by AssetManager/openFd, bundle CRC, and relevant resource bytes. Remove split-required/PAD declarations only after obtaining content and proving the loader can access its merged location.

Use exact structured Manifest deletion and compare components, attributes, and metadata. Verify unselected WorkManager, Firebase, and ad components remain intact. When disabling PAD managers, inspect JNI missing-API paths, listeners, and synchronous wrappers; do not fabricate successful download events.

## Verify and deliver

Cover first-install/no-cache cold starts, existing-save recovery, normal downloads, missing/failing/cancelled downloads, scene/audio transitions, and selected offline paths. Clear caches or disconnect networking only in authorized isolated environments; do not erase user-device caches for testing convenience.

Record actual cache conditions and resource coverage. A warm-cache test does not prove fully offline first startup. Report complete level tables separately from missing scenes/events. Deliver the resource index, sources/versions, integrity results, loading-route changes, and coverage gaps.
