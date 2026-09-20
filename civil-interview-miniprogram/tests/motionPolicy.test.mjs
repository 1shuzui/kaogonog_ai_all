import test from 'node:test'
import assert from 'node:assert/strict'
import { motionStyle, bottomInset, summaryState } from '../src/motion/policy.mjs'
import { createPresence } from '../src/motion/presence.mjs'

test('safe area is in logical px and is counted once, missing geometry is harmless', () => {
  assert.equal(bottomInset({ screenHeight: 844, safeArea: { bottom: 810 } }), 34)
  assert.equal(bottomInset({ safeAreaInsets: { bottom: 20 }, screenHeight: 844, safeArea: { bottom: 810 } }), 20)
  assert.equal(bottomInset({}), 0)
  assert.equal(bottomInset({ screenHeight: 10, safeArea: { bottom: 20 } }), 0)
})

test('off immediately has zero durations and reduced disables movement and loops', () => {
  assert.match(motionStyle('off'), /--motion-enter:0ms/)
  assert.match(motionStyle('off'), /--motion-scale:1;/)
  assert.match(motionStyle('reduced'), /--motion-offset:0px/)
  assert.match(motionStyle('reduced'), /--motion-segment:0ms/)
})

test('summary switches only across hysteresis boundaries', () => {
  assert.equal(summaryState(false, 99, 100, 20), false)
  assert.equal(summaryState(false, 101, 100, 20), true)
  assert.equal(summaryState(true, 99, 100, 20), true)
  assert.equal(summaryState(true, 81, 100, 20), true)
  assert.equal(summaryState(true, 79, 100, 20), false)
})

test('exit retains the node but disables clicks, stale completion cannot remove reopened content', () => {
  const callbacks = []; let state
  const p = createPresence({ publish: s => { state = s }, schedule: fn => { callbacks.push(fn); return callbacks.length }, cancel: () => {} })
  p.set(true, 200)
  assert.equal(state.mounted, true)
  p.set(false, 140)
  assert.equal(state.mounted, true)
  assert.equal(state.interactive, false)
  p.set(true, 200)
  callbacks[1]()
  assert.equal(state.mounted, true)
  assert.equal(state.interactive, true)
  p.finish(state.id)
  assert.equal(state.phase, 'shown')
})

test('disabled motion, hide and disposal converge immediately without leftover callbacks', () => {
  let state; let callback
  const p = createPresence({ publish: s => { state = s }, schedule: fn => { callback = fn; return 1 }, cancel: () => {} })
  p.set(true, 200); p.set(false, 0)
  assert.equal(state.mounted, false)
  callback()
  assert.equal(state.mounted, false)
  p.set(true, 200); p.set(true, 0)
  assert.equal(state.phase, 'shown')
  p.dispose(); callback()
  assert.equal(state.phase, 'shown')
})
