import test from 'node:test'
import assert from 'node:assert/strict'
import { effectScope, nextTick, ref } from 'vue'
import { useExamClock } from '../src/composables/useExamClock.mjs'
import { useFloatingCamera } from '../src/composables/useFloatingCamera.mjs'

function clock(t, question = {}, jiangsu = false) {
  let now = 1000, sequence = 0
  const timers = new Map(), scope = effectScope(), currentQuestion = ref(question)
  const state = scope.run(() => useExamClock({ question: currentQuestion,
    preferences: ref({ defaultPrepTime: 90, defaultAnswerTime: 180 }), isJiangsuFullExamTiming: ref(jiangsu)
  }, { now: () => now, setInterval: callback => { const id = ++sequence; timers.set(id, callback); return id }, clearInterval: id => timers.delete(id) }))
  t.after(() => scope.stop())
  state.resetQuestionClock()
  return { ...state, timers, scope, currentQuestion,
    at(value) { now = value }, tick(value) { now = value; for (const callback of [...timers.values()]) callback() } }
}

test('ordinary clock carries delayed preparation ticks into answering and overtime', t => {
  const f = clock(t, { prepTime: 2, answerTime: 3 })
  f.startTimer(); f.tick(5000)
  assert.equal(f.phase.value, 'answering')
  assert.equal(f.prepLeft.value, 0)
  assert.equal(f.answerLeft.value, 1)
  f.tick(7200)
  assert.equal(f.answerLeft.value, 0)
  assert.equal(f.overtimeSeconds.value, 1)
  assert.deepEqual(f.buildTimingMeta(), { actualSeconds: 7, standardSeconds: 5, overtimeSeconds: 2 })
})

test('Jiangsu early answering grants the shared fifteen minutes and later ticks keep that deadline', t => {
  const f = clock(t, {}, true)
  f.startTimer(); f.tick(61000)
  assert.equal(f.prepLeft.value, 240)
  f.beginJiangsuAnswer(); f.tick(181250)
  assert.equal(f.phase.value, 'answering')
  assert.equal(f.prepLeft.value, 0)
  assert.equal(f.answerLeft.value, 780)
  assert.equal(f.standardQuestionSeconds(), 1200)
})

test('repeated pause/resume excludes the capture wait exactly once', t => {
  const f = clock(t, { prepTime: 1, answerTime: 10 })
  f.startTimer(); f.tick(3000)
  f.at(4000); f.pauseCaptureClock(); f.pauseCaptureClock()
  f.tick(64000)
  assert.equal(f.currentUsageSeconds(), 3)
  assert.equal(f.answerLeft.value, 9)
  f.resumeCaptureClock(); f.resumeCaptureClock(); f.tick(65000)
  assert.equal(f.currentUsageSeconds(), 4)
  assert.equal(f.answerLeft.value, 7)
})

test('clock restart leaves one timer and scope disposal releases it', t => {
  const f = clock(t)
  f.startTimer(); f.startTimer()
  assert.equal(f.timers.size, 1)
  f.scope.stop()
  assert.equal(f.timers.size, 0)
  f.stopTimer()
  assert.equal(f.timers.size, 0)
})

function camera(t, windowInfo = () => ({ windowWidth: 375, windowHeight: 667 })) {
  let now = 1000
  const scope = effectScope(); t.after(() => scope.stop())
  const state = scope.run(() => useFloatingCamera({ now: () => now, getWindowInfo: windowInfo }))
  state.resetCameraPosition()
  return { ...state, at(value) { now = value } }
}
const touch = (x, y) => ({ touches: [{ clientX: x, clientY: y }] })

test('camera drag stays inside the viewport and suppresses accidental post-drag resizing', async t => {
  const f = camera(t)
  f.onCameraTouchStart(touch(300, 300)); f.onCameraTouchMove(touch(-1000, -1000)); f.onCameraTouchEnd()
  assert.equal(f.floatingCameraStyle.value, 'left:9px;top:9px;')
  f.at(1100); f.handleCameraTap(); f.at(1200); f.handleCameraTap()
  assert.equal(f.cameraSizeClass.value, 'floating-camera--small')
  f.at(2000); f.handleCameraTap(); f.at(2200); f.handleCameraTap(); await nextTick()
  assert.equal(f.cameraSizeClass.value, 'floating-camera--medium')
})

test('camera size changes reclamp its position instead of moving the window offscreen', async t => {
  const f = camera(t)
  f.onCameraTouchStart(touch(0, 0)); f.onCameraTouchMove(touch(2000, 2000)); f.onCameraTouchEnd()
  f.cycleCameraSize(); await nextTick()
  assert.equal(f.floatingCameraStyle.value, 'left:260px;top:461px;')
  assert.equal(f.cameraSizeText.value, '中窗 · 可拖动')
})

test('camera falls back to default viewport dimensions when platform metrics fail', t => {
  const f = camera(t, () => { throw new Error('unavailable') })
  assert.equal(f.floatingCameraStyle.value, 'left:289px;top:490px;')
})
