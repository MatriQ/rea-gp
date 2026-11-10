# Agent integration and portability

The shared workflow uses the [Agent Skills directory format](https://agentskills.io/specification): a `SKILL.md` entry point, relative references, and executable helpers. Install the same directory in a host-supported skills location. Discovery and invocation differ by host; the analysis and patch plans remain the same.

## Install one complete skill

Keep `SKILL.md`, `references/`, and `scripts/` together under a directory named `rea-gp`. Keep `agents/openai.yaml` when using Codex; it is optional metadata for that integration and can be ignored by other hosts. Exclude `.git`, `node_modules`, caches, signing material, and target artifacts from a skill-directory deployment copy.

Choose a project installation when sharing the workflow with a repository, or a user installation for local reuse. Avoid installing conflicting copies under the same name in multiple discovery roots. Use the host's skill list or refresh mechanism to confirm which copy is loaded. The bilingual READMEs list concrete installation paths and invocation examples.

Cloud or remote agent sessions need the skill and tools in their own runtime. A local installation does not establish that a remote worker can read the same files, run the Android toolchain, or contact a phone connected to the user's computer. Verify the actual execution location and connectivity before runtime work.

## DeepSeek Harness

### Plugin installation

The npm package `dsh-rea-gp` contributes a bundle layer through `cordis.patch.yml`. Its provider registers `rea-gp` from the existing `SKILL.md`, with the installed package root as the resource base. Packaged skills use rank 600, allowing a project or user copy in the same registry layer to override the bundled copy. The provider registration follows the plugin lifecycle and is removed when the plugin is unloaded.

Install from npm with `dsh plugin --profile demo add dsh-rea-gp@0.1.0`. For local development, prepare a checkout with `npm ci`, then install it using `dsh plugin --profile demo add /absolute/path/to/rea-gp`. Alternatively, run `npm pack` and install the resulting `.tgz` with the same command. The bundle ships plain JavaScript and needs no build step. It targets Node.js 24.9+ and Harness `^0.2.2-rc.1`; automated registry tests use `0.2.2-rc.1`.

The profile must supply `@deepseek-ai/dsh-skill` and `@deepseek-ai/dsh-tool-skill` (provided by the standard base bundle). The plugin supplies its own provider, so `@deepseek-ai/dsh-skill-filesystem` is optional for this route. No filesystem discovery copy is needed. Verify composition with `dsh --profile demo --dump-config`, then start that profile and invoke `/rea-gp`.

Run `npm test` for provider registration, resource access, local override priority, teardown, and tarball checks. These checks do not exercise a model conversation or Android/device work.

### Directory installation

For native filesystem discovery, use the existing skill directory unchanged. The active profile needs these plugins (a composition fragment, not a complete profile):

```yaml
- name: '@deepseek-ai/dsh-skill'
- name: '@deepseek-ai/dsh-skill-filesystem'
- name: '@deepseek-ai/dsh-tool-skill'
```

Install at `<projectRoot>/.dsh/skills/rea-gp/` or `${DSH_HOME:-$HOME/.dsh}/skills/rea-gp/`. Shared `.agents/skills/rea-gp/` project and user roots are also supported; `DSH_AGENTS_HOME` overrides the default user `~/.agents` root. These paths require the filesystem provider's default roots to be enabled. Discovery checks direct skill bundles, so avoid an extra directory such as `skills/rea-gp/rea-gp/SKILL.md`. With no `.git` ancestor, the session's current directory becomes the project root.

Invoke `/rea-gp` with the task, or ask the agent to load `rea-gp` using the `skill` tool. Confirm the loaded instruction path identifies the intended copy, then follow [Check an integration](#check-an-integration) to verify references and helper execution. Use [manual loading](#manual-loading-without-native-skills) if native skill plugins are unavailable. Python, Android tools, and optional REA/MCP services still need to be accessible in the Harness runtime.

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
- [DeepSeek Harness filesystem skills](https://github.com/deepseek-ai/deepseek-harness/blob/master/packages/skill/skill-filesystem/README.md) and [skill loader](https://github.com/deepseek-ai/deepseek-harness/blob/master/packages/skill/tool-skill/README.md): discovery roots, required plugins, and `/rea-gp` invocation.
- [DeepSeek Harness plugin packaging](https://github.com/deepseek-ai/deepseek-harness/blob/master/docs/user/develop/basic/publish.md) and [bundled Office skill provider](https://github.com/deepseek-ai/deepseek-harness/blob/master/packages/skill/skill-office/src/index.ts): bundle installation and packaged skill resources.
- [Claude Code skills](https://code.claude.com/docs/en/skills): `.claude/skills` discovery and `/rea-gp` invocation.
- [Cursor skills](https://cursor.com/docs/skills): `.cursor/skills` discovery and selection from the `/` menu.
- [OpenCode skills](https://opencode.ai/docs/skills/): `.opencode/skills` discovery and the native skill-loading tool.
- [Gemini CLI skills](https://geminicli.com/docs/cli/skills/): `.gemini/skills` discovery and skill management.

Use current host documentation when paths, settings, or discovery behavior differ in the installed version. Keep host-specific settings outside the shared workflow.
