import test from 'node:test'
import assert from 'node:assert/strict'
import { parse } from 'acorn'
import { mkdtempSync, readFileSync, writeFileSync, mkdirSync, rmSync } from 'node:fs'
import { join } from 'node:path'
import { tmpdir } from 'node:os'
import { build } from 'vite'
import { nativeTabBar } from '../scripts/native-tab-bar.mjs'

test('native navigation JavaScript is emitted with upload-compatible syntax', async () => {
  const previous = process.env.UNI_PLATFORM
  process.env.UNI_PLATFORM = 'mp-weixin'
  const files = []
  try {
    await nativeTabBar().generateBundle.call({
      addWatchFile() {},
      emitFile(asset) { files.push(asset) }
    })
  } finally {
    if (previous === undefined) delete process.env.UNI_PLATFORM
    else process.env.UNI_PLATFORM = previous
  }
  const scripts = files.filter(file => file.fileName.endsWith('.js'))
  assert.ok(scripts.some(file => file.fileName === 'custom-tab-bar/index.js'))
  assert.ok(scripts.some(file => file.fileName === 'custom-tab-bar/navigation.js'))
  for (const file of scripts) {
    assert.doesNotThrow(() => parse(file.source, { ecmaVersion: 2018, sourceType: 'script' }), file.fileName)
  }
})

test('native syntax remains compatible after framework copy hooks run', async () => {
  const previous = process.env.UNI_PLATFORM
  process.env.UNI_PLATFORM = 'mp-weixin'
  const root = mkdtempSync(join(tmpdir(), 'wechat-build-'))
  const outDir = join(root, 'dist')
  writeFileSync(join(root, 'entry.js'), 'export const value = 1')
  try {
    await build({
      configFile: false, root, logLevel: 'silent',
      plugins: [nativeTabBar(), {
        name: 'copy-native-like-uni-app',
        writeBundle() {
          const directory = join(outDir, 'custom-tab-bar')
          mkdirSync(directory, { recursive: true })
          writeFileSync(join(directory, 'index.js'), readFileSync('src/custom-tab-bar/index.js'))
        }
      }],
      build: { outDir, lib: { entry: join(root, 'entry.js'), formats: ['cjs'] } }
    })
    parse(readFileSync(join(outDir, 'custom-tab-bar/index.js'), 'utf8'), { ecmaVersion: 2018, sourceType: 'script' })
  } finally {
    if (previous === undefined) delete process.env.UNI_PLATFORM
    else process.env.UNI_PLATFORM = previous
    rmSync(root, { recursive: true, force: true })
  }
})
