import test from 'node:test'
import assert from 'node:assert/strict'
import { createCollapse } from '../src/motion/collapse.mjs'

function fixture(open = true) {
  let state, clock = 0, serial = 0
  const measurements = [], timers = new Map()
  const collapse = createCollapse({ open, measure: () => new Promise(resolve => measurements.push(resolve)), publish: value => { state = value }, now: () => clock,
    schedule: fn => { const id = ++serial; timers.set(id, fn); return id }, cancel: id => timers.delete(id) })
  const reply = async value => { measurements.shift()(value); await Promise.resolve(); await Promise.resolve() }
  return { collapse, reply, timers, state: () => state, advance: value => { clock += value } }
}

test('closing keeps the layout node, animates measured px height, then releases it once', async () => {
  const f = fixture()
  f.collapse.set(false, 280)
  await f.reply({ outer: 360, inner: 360 })
  const state = f.state()
  assert.equal(state.from, 360)
  assert.equal(state.to, 0)
  assert.equal(state.mounted, true)
  assert.equal(state.interactive, false)
  assert.equal(f.collapse.complete(state.id), false, 'Early/bubbled completion cannot cut off the transition')
  f.advance(280)
  f.collapse.complete(state.id)
  assert.equal(f.state().height, '0px')
  assert.equal(f.state().mounted, false)
  assert.equal(f.timers.size, 0)
})

test('fast reversal starts at current visible height and ignores old measurements/completions', async () => {
  const f = fixture()
  f.collapse.set(false, 280)
  f.collapse.set(true, 280)
  await f.reply({ outer: 360, inner: 360 })
  assert.notEqual(f.state().phase, 'closing')
  await f.reply({ outer: 137, inner: 360 })
  assert.equal(f.state().from, 137)
  assert.equal(f.state().to, 360)
  const old = f.state().id
  f.collapse.set(false, 280)
  await f.reply({ outer: 202, inner: 360 })
  f.advance(300)
  f.collapse.complete(old)
  assert.equal(f.state().mounted, true)
  f.collapse.complete(f.state().id)
  assert.equal(f.state().mounted, false)
})

test('content replacement freezes the previous natural height before measuring the new result', async () => {
  const f = fixture(false)
  f.collapse.set(true, 0)
  await f.reply({ outer: 0, inner: 180 })
  assert.equal(f.state().height, 'auto')
  f.collapse.resize(280)
  assert.equal(f.state().height, '180px')
  await f.reply({ outer: 180, inner: 520 })
  assert.equal(f.state().from, 180)
  assert.equal(f.state().to, 520)
  f.advance(280); f.collapse.complete(f.state().id)
  assert.equal(f.state().height, 'auto')
})

test('hidden pages keep their occupied height; stale work stops and resume settles the latest target', async () => {
  const f = fixture()
  f.collapse.set(false, 280)
  await f.reply({ outer: 350, inner: 350 })
  const before = f.state()
  f.collapse.pause()
  assert.equal(f.timers.size, 0)
  assert.equal(f.state(), before)
  f.collapse.set(true, 280)
  assert.equal(f.state(), before, 'Do not publish visual changes while hidden')
  f.collapse.resume(0)
  await f.reply({ outer: 210, inner: 350 })
  assert.equal(f.state().height, 'auto')
  f.collapse.dispose()
  f.collapse.set(false, 280)
  assert.equal(f.state().height, 'auto')
})
