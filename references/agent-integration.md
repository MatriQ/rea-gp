# Agent integration and portability

The shared workflow uses the [Agent Skills directory format](https://agentskills.io/specification): a `SKILL.md` entry point, relative references, and executable helpers. Install the same directory in a host-supported skills location. Discovery and invocation differ by host; the analysis and patch plans remain the same.

## Install one complete skill

Keep `SKILL.md`, `references/`, and `scripts/` together under a directory named `rea-gp`. Keep `agents/openai.yaml` when using Codex; it is optional metadata for that integration and can be ignored by other hosts. Exclude `.git`, caches, signing material, and target artifacts from a deployment copy.

Choose a project installation when sharing the workflow with a repository, or a user installation for local reuse. Avoid installing conflicting copies under the same name in multiple discovery roots. Use the host's skill list or refresh mechanism to confirm which copy is loaded. The bilingual READMEs list concrete installation paths and invocation examples.

Cloud or remote agent sessions need the skill and tools in their own runtime. A local installation does not establish that a remote worker can read the same files, run the Android toolchain, or contact a phone connected to the user's computer. Verify the actual execution location and connectivity before runtime work.

## Map capabilities rather than tool names

| Capability | Host adaptation | When unavailable |
| --- | --- | --- |
| Find/download a game package | Use the host's search/browser or `acquire_package.py` against public source pages. Follow [package-acquisition.md](package-acquisition.md) for identity and variant decisions. | Reuse a local artifact or identify the missing source access without claiming a download succeeded. |
| Read files and references | Use the host's file tools or shell; resolve links relative to the loaded file and script paths from the skill root. | Work with supplied text/artifacts and identify files still needed. |
| Execute helpers and analysis tools | Use the host's shell or process tool with an explicit working directory and absolute input/output paths. Select Python and Android tools in that environment. | Provide analysis and reproducible commands, with execution marked pending. |
| Preserve evidence | Store hashes, exact commands, tool versions, observations, and outputs in the task workspace. Use actual REA Evidence IDs only when supplied by REA. | Distinguish unavailable evidence from inference; do not invent identifiers. |
| Ask a material scope question | Use host-native interaction or a concise chat question, reusing prior user choices. | Continue work independent of the missing choice; do not treat silence as an answer. |
| Access a test device | Use the selected runtime's ADB and an explicitly chosen device serial, within the requested installation/testing scope. | Finish independent analysis/build work and state the untested device paths. |
| Use REA or other MCP services | Discover the host's actual connected tools and use their supported contracts. CLI/local analysis is an alternative. | Continue without MCP when local tools cover the task; identify any remaining provider gap. |

The skill does not grant permissions, configure MCP servers, install Android tools, or provide device access. Follow the current host's execution controls and the user's authorized scope.

## Manual loading without native skills

Keep the complete skill directory accessible, then give the agent a prompt such as:

```text
Read /absolute/path/to/rea-gp/SKILL.md and follow its workflow for this task.
Resolve bundled references and scripts from /absolute/path/to/rea-gp.
Analyze /absolute/path/to/game.xapk and disable the selected Google Play
integrations while preserving normal gameplay. Preserve downloads, Firebase,
ads, rewards, and backend behavior unless I select a change separately.
Keep generated files in /absolute/path/to/task-workspace and report what
you actually verified with the tools available in this session.
```

This route needs no special command prefix. If the host only accepts pasted instructions, provide the Markdown body and relevant reference contents, preserving their source paths. Script execution still requires access to the actual files and a suitable runtime.

In examples, `SKILL_ROOT` means the resolved directory containing the loaded `SKILL.md`; it is not a predefined environment variable. For example, after filling the real path in a POSIX shell:

```bash
skill_root="/absolute/path/to/rea-gp"
python3 "$skill_root/scripts/doctor_tools.py" --probe
python3 "$skill_root/scripts/inventory_package.py" /absolute/path/to/game.xapk --nested
```

On another shell, use its native quoting and absolute paths. Do not assume a host-specific variable, shell syntax, or skill invocation prefix is portable.

## Check an integration

Confirm the host loads this skill's name/description and can follow one relative reference. Run a helper's `--help` from outside the installed directory using its absolute path. For execution tasks, confirm Python/tool compatibility and explicit task input/output paths. Test device visibility only when device work is within scope.

Native discovery, successful helper execution, and successful target installation/runtime behavior are separate checks. Report the hosts and conditions actually tested. Documentation-based installation support does not establish an end-to-end test in every host.

## Host documentation

- [Agent Skills specification](https://agentskills.io/specification): shared directory, frontmatter, and reference format.
- [Claude Code skills](https://code.claude.com/docs/en/skills): `.claude/skills` discovery and `/rea-gp` invocation.
- [Cursor skills](https://cursor.com/docs/skills): `.cursor/skills` discovery and selection from the `/` menu.
- [OpenCode skills](https://opencode.ai/docs/skills/): `.opencode/skills` discovery and the native skill-loading tool.
- [Gemini CLI skills](https://geminicli.com/docs/cli/skills/): `.gemini/skills` discovery and skill management.

Use current host documentation when paths, settings, or discovery behavior differ in the installed version. Keep host-specific settings outside the shared workflow.
