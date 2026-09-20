import test from 'node:test'
import assert from 'node:assert/strict'
import { mkdtempSync, mkdirSync, writeFileSync, rmSync } from 'node:fs'
import { tmpdir } from 'node:os'
import { join } from 'node:path'
import { validateMotionAssets } from '../scripts/validate-motion-assets.mjs'

function fixture(t) {
  const root = mkdtempSync(join(tmpdir(), 'kaogong-motion-'))
  t.after(() => rmSync(root, { recursive: true, force: true }))
  mkdirSync(join(root, 'custom-tab-bar'), { recursive: true })
  writeFileSync(join(root, 'app.json'), JSON.stringify({ tabBar: { custom: true, list: [{ pagePath: 'pages/home/index' }] } }))
  writeFileSync(join(root, 'custom-tab-bar/tabs.js'), 'module.exports = [{"pagePath":"pages/home/index"}]')
  writeFileSync(join(root, 'custom-tab-bar/index.js'), "const tokens = require('./tokens.js')")
  writeFileSync(join(root, 'custom-tab-bar/index.json'), '{"component":true}')
  for (const name of ['navigation.js', 'tokens.js', 'index.wxml', 'index.wxss']) writeFileSync(join(root, 'custom-tab-bar', name), 'fixture')
  writeFileSync(join(root, 'app.wxss'), '.motion-page{animation:none}.motion-page--off{color:inherit}')
  return root
}

test('native navigation ships native assets with matching configured tab routes', t => {
  assert.deepEqual(validateMotionAssets(fixture(t)), [])
})
test('rejects JSON require that compiles but prevents the native tabBar from loading', t => {
  const root = fixture(t)
  writeFileSync(join(root, 'custom-tab-bar/index.js'), "const tokens = require('./tokens.json')")
  assert.ok(validateMotionAssets(root).some(x => x.includes('JSON')))
})
test('rejects missing native files, route drift and dropped motion CSS', t => {
  const root = fixture(t)
  rmSync(join(root, 'custom-tab-bar/navigation.js'))
  writeFileSync(join(root, 'custom-tab-bar/tabs.js'), 'module.exports = []')
  writeFileSync(join(root, 'app.wxss'), '')
  assert.equal(validateMotionAssets(root).length, 3)
})

test('requires the real native scroll hook, not just a composable in a successful JS build', t => {
  const root = fixture(t)
  const page = 'pages/home/index'
  mkdirSync(join(root, 'pages/home'), { recursive: true })
  writeFileSync(join(root, 'app.json'), JSON.stringify({ pages: [page], tabBar: { custom: true, list: [{ pagePath: page }] } }))
  writeFileSync(join(root, page + '.wxml'), '<view class="motion-page"/>')
  writeFileSync(join(root, page + '.js'), 'useScrollSummary()')
  assert.ok(validateMotionAssets(root).some(x => x.includes('onPageScroll')))
  writeFileSync(join(root, page + '.js'), 'page.__runtimeHooks=1')
  assert.deepEqual(validateMotionAssets(root), [])
})
