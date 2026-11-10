import { readFile } from 'node:fs/promises'
import { sep } from 'node:path'
import { fileURLToPath } from 'node:url'
import { parse } from 'yaml'

export const name = 'rea-gp'
export const inject = ['skills']

const providerName = 'rea-gp-bundled'
const skillPath = fileURLToPath(new URL('../SKILL.md', import.meta.url))
const skillRoot = fileURLToPath(new URL('../', import.meta.url)).split(sep).join('/')
// Harness reserves rank 600 for packaged skill providers; local copies take priority.
const bundledSkillRank = 600

async function loadSkill(signal) {
  const raw = await readFile(skillPath, { encoding: 'utf8', signal })
  const header = /^---\r?\n([\s\S]*?)\r?\n---(?:\r?\n|$)/u.exec(raw)
  if (!header) throw new Error(`rea-gp: missing YAML frontmatter in ${skillPath}`)
  const metadata = parse(header[1])
  if (!metadata || metadata.name !== name || typeof metadata.description !== 'string'
      || !metadata.description.trim()) {
    throw new Error(`rea-gp: ${skillPath} must declare name: rea-gp and a nonempty description`)
  }
  return {
    name: metadata.name,
    description: metadata.description,
    path: skillPath,
    invocation: { modelInvocable: true, userInvocable: true },
    source: 'bundled',
    provider: providerName,
    resourceBase: { kind: 'directory', path: skillRoot },
    content: raw.slice(header[0].length).trim(),
  }
}

export function apply(ctx) {
  ctx.skills.registerProvider(() => ({
    name: providerName,
    async list(options) {
      const { content, ...summary } = await loadSkill(options.signal)
      return [{ ...summary, rank: bundledSkillRank, locator: skillPath }]
    },
    async get(candidate, options) {
      if (candidate.name !== name) return undefined
      return loadSkill(options.signal)
    },
  }))
}
