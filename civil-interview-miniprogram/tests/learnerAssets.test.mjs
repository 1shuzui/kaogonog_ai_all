import test from 'node:test'
import assert from 'node:assert/strict'
import { mkdtempSync, mkdirSync, writeFileSync, rmSync } from 'node:fs'
import { tmpdir } from 'node:os'
import { join } from 'node:path'
import { learnerIconNames, validateLearnerAssets } from '../scripts/validate-learner-assets.mjs'

function fixture(t) {
  const root = mkdtempSync(join(tmpdir(), 'kaogong-learner-assets-'))
  t.after(() => rmSync(root, { recursive: true, force: true }))
  mkdirSync(join(root, 'static/learner-icons'), { recursive: true })
  mkdirSync(join(root, 'components'), { recursive: true })
  writeFileSync(join(root, 'components/RoomActions.wxss'), '.room-actions{display:grid;grid-template-columns:180rpx 1fr}')
  writeFileSync(join(root, 'app.wxss'), ['home', 'prepare', 'room', 'result'].map(page => `.learner-page.learner-${page}{color:#203047}`).join(''))
  for (const name of learnerIconNames) {
    writeFileSync(join(root, `static/learner-icons/${name}.svg`), '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24"><path d="M0 0h24v24z"/></svg>')
  }
  return root
}

test('accepts a build containing all four learner themes and standalone local icons', t => {
  assert.deepEqual(validateLearnerAssets(fixture(t)), [])
})

test('rejects a successful JS build that dropped the learner WXSS', t => {
  const root = fixture(t)
  writeFileSync(join(root, 'app.wxss'), '.page{padding:28rpx}')
  writeFileSync(join(root, 'learner.js'), '"use strict";')
  const failures = validateLearnerAssets(root)
  assert.equal(failures.length, 4)
  assert.ok(failures.every(value => value.includes('theme')))
})

test('rejects inline-only SVGs that fail to load as mini-program images', t => {
  const root = fixture(t)
  writeFileSync(join(root, 'static/learner-icons/audio.svg'), '<svg viewBox="0 0 24 24"><path d="M0 0h24v24z"/></svg>')
  assert.deepEqual(validateLearnerAssets(root), ['static/learner-icons/audio.svg must be a standalone SVG with the SVG namespace'])
})

test('rejects a missing icon and an SVG that lost its vector paths', t => {
  const root = fixture(t)
  rmSync(join(root, 'static/learner-icons/audio.svg'))
  writeFileSync(join(root, 'static/learner-icons/aim.svg'), '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24"/>')
  const failures = validateLearnerAssets(root)
  assert.ok(failures.includes('missing learner asset: static/learner-icons/audio.svg'))
  assert.ok(failures.includes('static/learner-icons/aim.svg must retain its viewBox and vector paths'))
})

test('rejects a room whose footer layout exists only in the parent page scope', t => {
  const root = fixture(t)
  writeFileSync(join(root, 'components/RoomActions.wxss'), '')
  assert.ok(validateLearnerAssets(root).some(value => value.startsWith('RoomActions.wxss must own')))
})
