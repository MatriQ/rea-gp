# General equal-length binary patch plans

`scripts/apply_verified_patches.py` applies analyzed and verified byte replacements. It does not discover gates, decrypt initialization, encode branches, or sign APKs. File-offset patches accept arbitrary binary inputs; virtual-address patches require parseable ELF32/ELF64.

## Fields

| Field | Meaning |
| --- | --- |
| `input_sha256` | Required full SHA-256 of the current input stage. |
| `output_sha256` | Use when an independently expected result exists; omit when unknown. Do not conceal differences with an unverified value. |
| `patches` | Non-empty array of equal-length replacements. |
| `patches[].name` | Optional feature label. |
| `patches[].file_offset` | Zero-based non-negative integer or hexadecimal string prefixed with `0x`. |
| `patches[].virtual_address` | Optional ELF **link-time VA**. Subtract actual load bias from runtime addresses first. The script maps through the file's PT_LOAD segments. |
| `patches[].before` / `after` | Non-empty hexadecimal byte strings of equal length. |

Provide at least one address per patch. If both are supplied, their mappings must agree. The entire VA range must fit in one file-backed load segment, not memory-only BSS. Retain rationale, disassembly, evidence references, and other review fields; the script does not execute those additional fields as instructions.

Handle the Thumb mode bit in ARM method pointers separately from instruction addresses. Do not treat tagged pointers as file offsets; the script does not guess or clear address tags for callers.

See [patch-plan.schema.json](patch-plan.schema.json) for machine-readable structure. The patch script additionally checks cross-field lengths, actual bytes, source hashes, overlaps, and ELF mappings.

## Generate and execute

1. Hash the actual current input and read preimage bytes at established locations.
2. Generate replacements from disassembly and feature evidence. Verify ABI, instruction boundaries, and branch destinations.
3. Write actual values to a JSON plan in the task directory. Do not copy addresses/hashes from another game or version.
4. Check with `--dry-run`, then write to a new path with `--output` after reviewing the plan.
5. Independently disassemble the output and check ELF/expected differences, then perform runtime verification on the same build artifact.

The script rejects in-place changes, existing outputs, and existing output symlinks. It publishes a new file only after all replacements pass verification. `patches_verified` means the byte plan passed checks, not that the target starts or behaves correctly.
