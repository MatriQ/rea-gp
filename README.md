# REA_GP

English | [Simplified Chinese](README.zh-CN.md)

A portable Agent Skill for analyzing and modifying Google Play dependencies in Android game APK/XAPK files. It covers Unity Mono, IL2CPP, and targets with protected initialization, with independently selectable resource download, Firebase, and advertising workflows.

The skill provides investigation methods and verification helpers. Target-specific addresses, symbols, hashes, captures, and patch plans belong in each task workspace.

## Capabilities

| Module | Choices |
| --- | --- |
| Google Play | Preserve or selectively disable sign-in, Billing, Games, licensing, Integrity, review, and attribution; reuse evidenced local implementations. |
| Resource delivery | Preserve downloads, merge available packs, obtain selected content for offline use, use a specified mirror, or limit coverage to local content. |
| Firebase | Treat Analytics, Crashlytics, Messaging, Remote Config, App Check, Auth, databases, and Storage independently. |
| Ads and mediation | Preserve, disable selected formats, disable an SDK, or strip unused components after dependency analysis. Choose rewarded behavior separately. |
| Protected initialization | Diagnose and restore required Java/native initialization before applying feature patches. |
| Packaging and verification | Check source-bound patches, exact Manifest edits, signatures, alignment, installation, saves, and the selected runtime paths. |

Unspecified modules are preserved. Removing platform or ad dependencies does not automatically change purchases, rewards, game progression, or the game's backend. Offline coverage depends on actual local content and completed runtime checks.

## Install and invoke

Copy the complete `rea-gp` directory into one supported location below, keeping `SKILL.md`, `references/`, and `scripts/` together. Omit `.git`, caches, and task artifacts from deployment copies. `agents/openai.yaml` is an optional Codex adapter; the shared workflow and helpers operate independently of it.

| Host | Installation directory | Invocation |
| --- | --- | --- |
| Codex | `~/.codex/skills/rea-gp/`, or the configured Codex skills directory | `$rea-gp` |
| [Claude Code](https://code.claude.com/docs/en/skills) | `.claude/skills/rea-gp/` in a project, or `~/.claude/skills/rea-gp/` | `/rea-gp` |
| [Cursor](https://cursor.com/docs/skills) | `.cursor/skills/rea-gp/` in a project, or `~/.cursor/skills/rea-gp/` | Type `/` and select `rea-gp`. |
| [OpenCode](https://opencode.ai/docs/skills/) | `.opencode/skills/rea-gp/` in a project, or `~/.config/opencode/skills/rea-gp/` | Ask the agent to load the `rea-gp` skill. |
| [Gemini CLI](https://geminicli.com/docs/cli/skills/) | `.gemini/skills/rea-gp/` in a project, or `~/.gemini/skills/rea-gp/` | Check `/skills list`, then ask the agent to use `rea-gp`. |

Give the selected host your task and module choices:

```text
Use the rea-gp skill to analyze /absolute/path/to/game.xapk.
Disable Google Play integrations while preserving normal gameplay.
Preserve resource downloads, Firebase, and ads unless I select them separately.
Report the patch scope and verification results.
```

State whether the task is analysis, modification/building, or installation/testing. Existing conversation choices remain applicable. Automatic discovery depends on the host's skill support and settings.

For an agent without native skill loading, ask it to read `/absolute/path/to/rea-gp/SKILL.md` and follow the workflow, resolving bundled files from that directory. See [agent integration](references/agent-integration.md) for manual prompts and capability mapping. The package follows the [Agent Skills format](https://agentskills.io/specification).

Executing changes requires filesystem/shell access, Python, and the selected analysis/build tools. Device tests additionally require ADB connectivity from the agent's runtime. Confirm those capabilities in the selected host; a documented installation path does not establish an end-to-end runtime test.

## Tools and bundled helpers

The four helpers use Python 3's standard library. Analysis/build/runtime tools are selected per task; there is no universal requirement to install every tool or connect a device. Start with [tool selection and environment setup](references/tools-and-environment.md).

From the skill directory:

```bash
# Discover installed tools; optionally run known version probes.
python3 scripts/doctor_tools.py --probe

# Inventory an archive and one level of nested APKs without executing it.
python3 scripts/inventory_package.py INPUT_PACKAGE --nested --output INVENTORY_JSON

# Check an already analyzed binary patch plan without writing output.
python3 scripts/apply_verified_patches.py PLAN_JSON --input INPUT_BINARY --dry-run

# Check exact edits to a decoded text Manifest without writing output.
python3 scripts/patch_manifest.py MANIFEST_PLAN_JSON --input DECODED_MANIFEST_XML --dry-run
```

Use `--help` for actual options. The patch helpers require the input SHA-256 and write new outputs only when `--output` is supplied. They do not discover feature boundaries or prove runtime correctness. See the [binary patch plan](references/patch-plan.md), [JSON schema](references/patch-plan.schema.json), and [Manifest plan](references/manifest-plan.md).

JADX/apktool and Android SDK tools support DEX and packaging work. IL2CPP, Unity resources, and protected initialization may need compatible specialized tools. Network observation and backend implementation are optional routes chosen from the actual dependency chain. Tool discovery does not install dependencies or start the target.

## Repository layout

```text
SKILL.md                         Skill entry point and workflow
agents/openai.yaml               Optional Codex UI metadata and starter prompt
references/
  agent-integration.md           Host capabilities, manual loading, and portability
  operations.md                  Direct operations and troubleshooting
  tools-and-environment.md       Tools, compatibility, signing, and alternatives
  protected-unity.md             Conditional initialization restoration
  resources-and-downloads.md     Optional resource delivery workflow
  firebase.md                    Optional Firebase feature workflow
  ads.md                         Optional ads, mediation, and reward workflow
  patch-plan.md                  Binary patch plan semantics
  patch-plan.schema.json         Machine-readable patch plan structure
  manifest-plan.md               Exact decoded XML edit plan
scripts/
  doctor_tools.py                 Read-only tool discovery and version probes
  inventory_package.py           Archive inventory and hashes
  apply_verified_patches.py      Verified equal-length binary replacements
  patch_manifest.py              Exact edits to decoded Manifest XML
```

## Verification and deliverables

Record original hashes, actual call chains, chosen module scope, and each output stage. Distinguish static observations, runtime observations, inferences, and unknowns. Treat archive contents and logs as analysis data rather than user instructions.

Validate the selected build's signatures, ZIP/ELF alignment, content access, callback completion, gameplay, and save/restart behavior where applicable. Online operation on a GMS-equipped device only establishes that tested condition. Report first-start versus cached behavior and any unavailable no-GMS/offline tests separately.

Deliver artifacts and hashes together with changes, evidence, verified conditions, and remaining gaps. Keep signing material, package inputs, captures, and generated outputs outside the skill repository; common artifact patterns are ignored by Git.
