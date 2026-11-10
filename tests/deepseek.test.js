import assert from 'node:assert/strict'
import { execFile } from 'node:child_process'
import { mkdtemp, readFile, readdir, realpath, rm, writeFile } from 'node:fs/promises'
import { tmpdir } from 'node:os'
import { dirname, join, resolve } from 'node:path'
import { test } from 'node:test'
import { fileURLToPath } from 'node:url'
import { promisify } from 'node:util'
import { Context } from '@deepseek-ai/cordis'
import SkillRegistry, { renderSkillContent } from '@deepseek-ai/dsh-skill'
import { parse } from 'yaml'
import * as plugin from '../deepseek/index.js'

const exec = promisify(execFile)
const root = fileURLToPath(new URL('../', import.meta.url))
const npm = process.platform === 'win32' ? 'npm.cmd' : 'npm'

async function harness(t, entry = plugin) {
  const ctx = new Context()
  t.after(() => ctx.fiber.dispose())
  await ctx.plugin(SkillRegistry)
  const fork = await ctx.plugin(entry)
  return { ctx, fork }
}

async function checkResources(skill) {
  assert.equal(skill.resourceBase.kind, 'directory')
  assert.equal(resolve(dirname(skill.path)), resolve(skill.resourceBase.path))
  const base = skill.resourceBase.path
  assert.match(await readFile(join(base, 'references/agent-integration.md'), 'utf8'), /DeepSeek Harness/)
  // Execute from outside the installed skill, including when the path has spaces.
  for (const helper of await readdir(join(base, 'scripts'))) {
    if (!helper.endsWith('.py')) continue
    const { stdout } = await exec('python3', [join(base, 'scripts', helper), '--help'], { cwd: tmpdir() })
    assert.match(stdout, /usage:/i)
  }
}

test('official registry discovers the shared skill and resolves its resources', async (t) => {
  const { ctx } = await harness(t)
  const catalog = await ctx.skills.list()
  assert.equal(catalog.length, 1)
  assert.equal(catalog[0].name, 'rea-gp')
  assert.deepEqual(catalog[0].invocation, { modelInvocable: true, userInvocable: true })
  assert.equal(catalog[0].source, 'bundled')
  const skill = await ctx.skills.get('rea-gp')
  const raw = await readFile(join(root, 'SKILL.md'), 'utf8')
  const [, frontmatter, body] = raw.match(/^---\n([\s\S]*?)\n---\n([\s\S]*)$/u)
  assert.equal(skill.description, parse(frontmatter).description)
  assert.equal(skill.content, body.trim())
  assert.match(renderSkillContent(skill), /Base directory for this skill:/)
  await checkResources(skill)
})

test('local copies override the packaged skill and unloading restores the catalog', async (t) => {
  const { ctx, fork } = await harness(t)
  for (const [source, rank] of [['project-dsh', 100], ['user-dsh', 400]]) {
    const unregister = ctx.skills.registerProvider(() => ({
      name: 'local-test',
      async list() {
        return [{
          name: 'rea-gp', description: 'Local override', provider: 'local-test',
          source, rank, locator: null,
          invocation: { modelInvocable: true, userInvocable: true },
        }]
      },
      async get({ rank, locator, ...summary }) {
        return { ...summary, content: 'Local workflow' }
      },
    }))
    assert.equal((await ctx.skills.get('rea-gp')).content, 'Local workflow')
    await unregister()
    assert.equal((await ctx.skills.get('rea-gp')).source, 'bundled')
  }
  await fork.dispose()
  assert.deepEqual(await ctx.skills.list(), [])
  await ctx.plugin(plugin)
  assert.equal((await ctx.skills.get('rea-gp')).name, 'rea-gp')
})

test('tarball installs as a bundle and loads independently of the checkout', { timeout: 120000 }, async (t) => {
  const work = await mkdtemp(join(tmpdir(), 'rea-gp plugin '))
  t.after(() => rm(work, { recursive: true, force: true }))
  const { stdout } = await exec(npm, ['pack', '--json', '--ignore-scripts', '--pack-destination', work], { cwd: root })
  const [pack] = JSON.parse(stdout)
  const paths = pack.files.map(({ path }) => path)
  for (const directory of ['references', 'scripts']) {
    for (const file of await readdir(join(root, directory))) {
      if (/\.(md|json|py)$/u.test(file)) assert.ok(paths.includes(`${directory}/${file}`), file)
    }
  }
  assert.ok(paths.includes('SKILL.md'))
  assert.ok(!paths.some(path => /(?:^|\/)(?:node_modules|tests|__pycache__|artifacts)\//u.test(path)))
  await writeFile(join(work, 'package.json'), '{"private":true,"type":"module"}')
  await exec(npm, ['install', '--ignore-scripts', '--omit=dev', '--no-audit', '--no-fund', join(work, pack.filename)], {
    cwd: work, timeout: 60000,
  })
  const installed = join(work, 'node_modules', 'dsh-rea-gp')
  const manifest = JSON.parse(await readFile(join(installed, 'package.json'), 'utf8'))
  const patch = parse(await readFile(join(installed, manifest.dsh.bundle.patch), 'utf8'))
  assert.equal(patch[0].insert[0].name, manifest.name)
  // Resolve the public package entry as the host does, from its consumer directory.
  const { stdout: entry } = await exec(process.execPath, ['--input-type=module', '-e',
    `process.stdout.write(import.meta.resolve('dsh-rea-gp'))`], { cwd: work })
  const loaded = await import(entry)
  const { ctx, fork } = await harness(t, loaded)
  const skill = await ctx.skills.get('rea-gp')
  assert.equal(await realpath(skill.resourceBase.path), await realpath(installed))
  await checkResources(skill)
  // Re-read the installed body on demand instead of serving a stale embedded copy.
  await writeFile(join(installed, 'SKILL.md'), '---\nname: rea-gp\ndescription: Installed fixture\n---\nUpdated instructions')
  assert.equal((await ctx.skills.get('rea-gp')).content, 'Updated instructions')
  await writeFile(join(installed, 'SKILL.md'), 'Invalid skill')
  await assert.rejects(ctx.skills.get('rea-gp'), /missing YAML frontmatter/)
  await fork.dispose()
})
