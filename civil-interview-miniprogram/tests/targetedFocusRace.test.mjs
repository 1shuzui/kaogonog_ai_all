import test from 'node:test'
import assert from 'node:assert/strict'
import { readFile } from 'node:fs/promises'
import vm from 'node:vm'
import * as pinia from 'pinia'
import * as targetedOptions from '../src/utils/targetedOptions.js'
import * as cancellation from '../src/utils/cancellation.mjs'

const FIRST_TARGET = { targetCode: 'jiangsu-general', province: 'jiangsu', position: 'general' }
const NEXT_TARGET = { targetCode: 'shandong-general', province: 'shandong', position: 'general' }

function deferred() {
  let resolve, reject
  const promise = new Promise((yes, no) => { resolve = yes; reject = no })
  return { promise, resolve, reject }
}

// Drain promise jobs without sleeping or advancing the injected scheduler.
const flush = () => new Promise(resolve => setImmediate(resolve))

function observe(promise) {
  const outcome = { settled: false, value: undefined, error: undefined }
  outcome.promise = promise.then(
    value => { outcome.settled = true; outcome.value = value },
    error => { outcome.settled = true; outcome.error = error }
  )
  return outcome
}

function createScheduler() {
  let now = 0, sequence = 0
  const timers = new Map()
  return {
    setTimeout(callback, delay) {
      const id = ++sequence
      timers.set(id, { at: now + delay, callback })
      return id
    },
    clearTimeout(id) { timers.delete(id) },
    get pendingCount() { return timers.size },
    async advanceBy(milliseconds) {
      const end = now + milliseconds
      while (true) {
        const next = [...timers].filter(([, timer]) => timer.at <= end)
          .sort((a, b) => a[1].at - b[1].at || a[0] - b[0])[0]
        if (!next) break
        const [id, timer] = next
        now = timer.at
        timers.delete(id)
        timer.callback()
        await flush()
      }
      now = end
      await flush()
    }
  }
}

async function createStore(t, getFocusAnalysis, timers = { setTimeout, clearTimeout }, api = {}) {
  const url = new URL('../src/stores/targeted.js', import.meta.url)
  // Capture the injected functions before evaluating the store module.
  const context = vm.createContext({ setTimeout: timers.setTimeout, clearTimeout: timers.clearTimeout })
  const module = new vm.SourceTextModule(await readFile(url, 'utf8'), {
    context, identifier: url.href
  })
  // Bridge real dependencies into the VM; replace only the API boundary.
  const imports = {
    pinia,
    '../utils/targetedOptions': targetedOptions,
    '../utils/cancellation.mjs': cancellation,
    '../api/targeted': {
      getFocusAnalysis,
      FOCUS_TIMEOUT_MS: 30000,
      FOCUS_SLOW_MS: 10000,
      getPositions: api.getPositions || (() => assert.fail('focus tests must not request the position tree')),
      generateQuestions: () => assert.fail('focus tests must not generate questions')
    }
  }
  await module.link(name => {
    const exports = imports[name]
    assert.ok(exports, `unexpected store dependency: ${name}`)
    return new vm.SyntheticModule(Object.keys(exports), function () {
      for (const [key, value] of Object.entries(exports)) this.setExport(key, value)
    }, { context })
  })
  await module.evaluate()
  const store = module.namespace.useTargetedStore(pinia.createPinia())
  t.after(() => {
    store.cancelFocusAnalysis?.()
    store.$dispose()
  })
  return store
}

test('late focus success after a target change cannot restore the previous target analysis', async t => {
  const response = deferred()
  const store = await createStore(t, () => response.promise)
  store.setTarget(FIRST_TARGET)
  const pending = store.fetchFocusAnalysis()
  assert.equal(store.focusLoading, true)

  store.setTarget(NEXT_TARGET)
  assert.equal(store.focusData, null)
  response.resolve({ targetCode: FIRST_TARGET.targetCode, summary: 'stale analysis' })
  const result = await pending

  assert.equal(store.selectionPayload.targetCode, NEXT_TARGET.targetCode)
  assert.equal(store.focusData, null, 'late success must not repopulate analysis cleared by setTarget')
  assert.equal(store.focusLoading, false)
  assert.equal(result, null, 'a superseded request returns no analysis to its caller')
})

test('an old focus request finishing cannot clear loading while the newer target request is pending', async t => {
  const oldResponse = deferred(), newResponse = deferred()
  const responses = [oldResponse, newResponse]
  const store = await createStore(t, () => responses.shift().promise)
  store.setTarget(FIRST_TARGET)
  const oldPending = store.fetchFocusAnalysis()
  store.setTarget(NEXT_TARGET)
  const newPending = store.fetchFocusAnalysis()
  assert.equal(store.focusLoading, true)

  oldResponse.resolve({ targetCode: FIRST_TARGET.targetCode, summary: 'stale analysis' })
  const oldResult = await oldPending
  const loadingWhileNewRequestPending = store.focusLoading

  // Settle both deferred responses before assertions, even when the regression is red.
  const latestData = { targetCode: NEXT_TARGET.targetCode, summary: 'latest analysis' }
  newResponse.resolve(latestData)
  await newPending

  assert.equal(loadingWhileNewRequestPending, true, 'old finally must not clear the newer request loading state')
  assert.deepEqual(store.focusData, latestData)
  assert.equal(store.focusLoading, false)
  assert.equal(store.focusStatus, 'success')
  assert.equal(oldResult, null)
})

test('resetting the target cannot let an in-flight focus response restore cleared analysis', async t => {
  const response = deferred()
  const store = await createStore(t, () => response.promise)
  store.setTarget(FIRST_TARGET)
  const pending = store.fetchFocusAnalysis()
  assert.equal(store.focusLoading, true)

  store.setTarget({})
  assert.equal(store.hasSelection, false)
  assert.equal(store.focusData, null)
  response.resolve({ targetCode: FIRST_TARGET.targetCode, summary: 'analysis after reset' })
  const result = await pending

  assert.equal(store.hasSelection, false)
  assert.equal(store.focusData, null, 'reset analysis must stay empty after the abandoned response resolves')
  assert.equal(store.focusLoading, false)
  assert.equal(result, null)
})

test('an equivalent normalized target preserves completed analysis; a different target clears it without fetching', async t => {
  const data = { targetCode: FIRST_TARGET.targetCode, summary: 'completed analysis' }
  const store = await createStore(t, async () => data)
  store.setTarget(FIRST_TARGET)
  assert.equal(store.focusLoading, false)
  assert.equal(store.focusStatus, 'idle')
  assert.deepEqual(await store.fetchFocusAnalysis(), data)

  store.setTarget({
    position: ' general ', province: ' jiangsu ', targetCode: ' jiangsu-general '
  })
  assert.deepEqual(store.focusData, data, 'normalization-equivalent selection must retain the last result')
  assert.equal(store.focusStatus, 'success')
  assert.equal(store.focusLoading, false)

  store.setTarget(NEXT_TARGET)
  assert.equal(store.focusData, null)
  assert.equal(store.focusStatus, 'idle')
  assert.equal(store.focusLoading, false, 'changing the target does not start a request')
})

test('cancelFocusAnalysis settles without an API response and ignores its later success', { timeout: 5000 }, async t => {
  const response = deferred()
  const lateData = { targetCode: FIRST_TARGET.targetCode, summary: 'cancelled analysis' }
  const store = await createStore(t, () => response.promise)
  t.after(() => response.resolve(lateData))
  store.setTarget(FIRST_TARGET)
  const pending = store.fetchFocusAnalysis()

  store.cancelFocusAnalysis()
  assert.equal(store.focusLoading, false)
  assert.equal(store.focusStatus, 'cancelled')
  assert.equal(await pending, null, 'stop must settle while the API promise is still pending')

  response.resolve(lateData)
  await flush()
  assert.equal(store.selectionPayload.targetCode, FIRST_TARGET.targetCode)
  assert.equal(store.focusData, null, 'late data must not restore a cancelled result')
  assert.equal(store.focusLoading, false)
  assert.equal(store.focusSlow, false)
  assert.equal(store.focusStatus, 'cancelled')
})

test('$reset followed by a new same-target request cannot revive the previous task', async t => {
  const oldResponse = deferred(), newResponse = deferred()
  const responses = [oldResponse, newResponse]
  const store = await createStore(t, () => responses.shift().promise)
  store.setTarget(FIRST_TARGET)
  const oldPending = store.fetchFocusAnalysis()

  store.$reset()
  store.setTarget(FIRST_TARGET)
  const newPending = store.fetchFocusAnalysis()
  oldResponse.resolve({ targetCode: FIRST_TARGET.targetCode, summary: 'before reset' })
  const oldResult = await oldPending
  const whileNewPending = {
    data: store.focusData, loading: store.focusLoading, status: store.focusStatus
  }
  const newData = { targetCode: FIRST_TARGET.targetCode, summary: 'after reset' }
  newResponse.resolve(newData)
  await newPending

  assert.deepEqual(whileNewPending, { data: null, loading: true, status: 'loading' },
    'reset must not let an old same-target task own the new request state')
  assert.equal(oldResult, null)
  assert.deepEqual(store.focusData, newData)
  assert.equal(store.focusLoading, false)
  assert.equal(store.focusStatus, 'success')
})

for (const [code, status] of [['NETWORK_ERROR', 'error'], ['REQUEST_TIMEOUT', 'timeout']]) {
  test(`a current ${code} failure publishes ${status} state and still rejects`, async t => {
    const response = deferred()
    const store = await createStore(t, () => response.promise)
    store.setTarget(FIRST_TARGET)
    const pending = store.fetchFocusAnalysis()
    assert.equal(store.focusStatus, 'loading')
    const error = Object.assign(new Error(`focus API ${code}`), { code })

    response.reject(error)
    await assert.rejects(pending, actual => actual === error)

    assert.equal(store.focusStatus, status)
    assert.equal(store.focusError, error.message)
    assert.equal(store.focusData, null)
    assert.equal(store.focusLoading, false)
    assert.equal(store.focusSlow, false)
  })
}

test('focusSlow starts at exactly 10 seconds and successful completion clears the remaining timer', async t => {
  const clock = createScheduler(), response = deferred()
  const store = await createStore(t, () => response.promise, clock)
  store.setTarget(FIRST_TARGET)
  const outcome = observe(store.fetchFocusAnalysis())
  assert.equal(clock.pendingCount, 2)

  await clock.advanceBy(9999)
  assert.equal(store.focusSlow, false)
  assert.equal(outcome.settled, false)
  await clock.advanceBy(1)
  assert.equal(store.focusSlow, true)
  assert.equal(store.focusLoading, true)
  assert.equal(store.focusStatus, 'loading')
  assert.equal(outcome.settled, false)

  const data = { targetCode: FIRST_TARGET.targetCode, summary: 'slow but successful' }
  response.resolve(data)
  await outcome.promise
  assert.equal(outcome.error, undefined)
  assert.deepEqual(outcome.value, data)
  assert.equal(store.focusSlow, false)
  assert.equal(clock.pendingCount, 0, 'success must remove the unexpired timeout')

  await clock.advanceBy(30000)
  assert.equal(store.focusStatus, 'success')
  assert.equal(store.focusLoading, false)
  assert.deepEqual(store.focusData, data)
})

test('the 30-second fallback times out an API that never settles and leaves no job timers', async t => {
  const clock = createScheduler()
  let signal
  const store = await createStore(t, (_, options) => {
    signal = options.signal
    return new Promise(() => {})
  }, clock)
  store.setTarget(FIRST_TARGET)
  const outcome = observe(store.fetchFocusAnalysis())

  await clock.advanceBy(29999)
  assert.equal(outcome.settled, false, 'the fallback must not reject before 30 seconds')
  assert.equal(store.focusLoading, true)
  assert.equal(store.focusSlow, true)
  assert.equal(signal.aborted, false)
  assert.equal(clock.pendingCount, 1)

  await clock.advanceBy(1)
  assert.equal(outcome.settled, true, 'the fallback must settle without help from the API')
  assert.equal(outcome.error?.code, 'REQUEST_TIMEOUT')
  assert.equal(store.focusStatus, 'timeout')
  assert.equal(store.focusError, outcome.error.message)
  assert.equal(store.focusData, null)
  assert.equal(store.focusLoading, false)
  assert.equal(store.focusSlow, false)
  assert.equal(signal.aborted, true)
  assert.equal(clock.pendingCount, 0)

  await clock.advanceBy(60000)
  assert.equal(store.focusStatus, 'timeout')
  assert.equal(store.focusError, outcome.error.message)
  assert.equal(clock.pendingCount, 0)
})

test('cancelling an older job clears only its timers and preserves the newer task deadlines', async t => {
  const clock = createScheduler(), oldResponse = deferred()
  const responses = [oldResponse.promise, new Promise(() => {})]
  const signals = []
  const store = await createStore(t, (_, options) => {
    signals.push(options.signal)
    return responses.shift()
  }, clock)
  store.setTarget(FIRST_TARGET)
  const oldOutcome = observe(store.fetchFocusAnalysis())
  await clock.advanceBy(5000)

  store.cancelFocusAnalysis()
  assert.equal(clock.pendingCount, 0, 'cancel must remove both unexpired timers immediately')
  assert.equal(signals[0].aborted, true)
  assert.equal(store.focusStatus, 'cancelled')
  store.setTarget(NEXT_TARGET)
  const newOutcome = observe(store.fetchFocusAnalysis())
  await flush()
  assert.equal(oldOutcome.settled, true)
  assert.equal(oldOutcome.value, null)
  assert.equal(oldOutcome.error, undefined)
  assert.equal(clock.pendingCount, 2, 'old finally must not clear the replacement timers')

  await clock.advanceBy(5000) // Old slow threshold; replacement is only 5 seconds old.
  assert.equal(store.focusSlow, false)
  assert.equal(store.focusLoading, true)
  await clock.advanceBy(5000) // Replacement reaches its own 10-second threshold.
  assert.equal(store.focusSlow, true)
  await clock.advanceBy(15000) // Old deadline; replacement is only 25 seconds old.
  oldResponse.resolve({ targetCode: FIRST_TARGET.targetCode, summary: 'obsolete analysis' })
  await flush()
  assert.equal(newOutcome.settled, false)
  assert.equal(store.focusStatus, 'loading')
  assert.equal(store.focusLoading, true)
  assert.equal(store.focusData, null)
  assert.equal(signals[1].aborted, false)
  assert.equal(clock.pendingCount, 1)

  await clock.advanceBy(4999)
  assert.equal(newOutcome.settled, false)
  await clock.advanceBy(1) // Replacement reaches its own 30-second deadline.
  assert.equal(newOutcome.settled, true)
  assert.equal(newOutcome.error?.code, 'REQUEST_TIMEOUT')
  assert.equal(store.focusStatus, 'timeout')
  assert.equal(store.focusLoading, false)
  assert.equal(store.focusSlow, false)
  assert.equal(signals[1].aborted, true)
  assert.equal(clock.pendingCount, 0)
})

test('duplicate focus clicks share one API request without postponing slow or timeout thresholds', async t => {
  const clock = createScheduler()
  let requests = 0
  const store = await createStore(t, () => { requests++; return new Promise(() => {}) }, clock)
  store.setTarget(FIRST_TARGET)
  const first = observe(store.fetchFocusAnalysis())
  const second = observe(store.fetchFocusAnalysis())
  assert.equal(requests, 1)
  assert.equal(clock.pendingCount, 2)

  await clock.advanceBy(9000)
  const third = observe(store.fetchFocusAnalysis())
  assert.equal(requests, 1)
  assert.equal(clock.pendingCount, 2)
  await clock.advanceBy(1000)
  assert.equal(store.focusSlow, true, 'duplicate clicks must not postpone the original slow threshold')

  await clock.advanceBy(19999)
  assert.deepEqual([first.settled, second.settled, third.settled], [false, false, false])
  await clock.advanceBy(1)
  assert.deepEqual([first.settled, second.settled, third.settled], [true, true, true],
    'every caller must settle at the original 30-second deadline')
  assert.deepEqual([first.error?.code, second.error?.code, third.error?.code],
    ['REQUEST_TIMEOUT', 'REQUEST_TIMEOUT', 'REQUEST_TIMEOUT'])
  assert.equal(requests, 1)
  assert.equal(store.focusStatus, 'timeout')
  assert.equal(store.focusLoading, false)
  assert.equal(store.focusSlow, false)
  assert.equal(clock.pendingCount, 0)
})

test('a failed position-tree load stays retryable and only a successful retry marks positionsLoaded', async t => {
  const firstResponse = deferred(), retryResponse = deferred()
  const responses = [firstResponse, retryResponse]
  const store = await createStore(t,
    () => assert.fail('position loading must not fetch focus analysis'), undefined,
    { getPositions: () => responses.shift().promise })
  assert.equal(store.positionsLoaded, false)

  const firstPending = store.fetchPositionTree()
  firstResponse.reject(new Error('fixture offline'))
  const fallback = await firstPending
  const loadedAfterFailure = store.positionsLoaded

  const retryPending = store.fetchPositionTree()
  const loadedWhileRetryPending = store.positionsLoaded
  const tree = [{ id: 'server-only-category', name: 'Server category', children: [] }]
  retryResponse.resolve({ tree, legacy: [] })
  const recovered = await retryPending

  // Exercise recovery before asserting the failed-request snapshot, even when red.
  assert.equal(loadedAfterFailure, false, 'a failed getPositions must leave positionsLoaded=false so the page can retry')
  assert.equal(loadedWhileRetryPending, false, 'an unresolved retry must not be marked successfully loaded')
  assert.deepEqual(fallback, targetedOptions.DEFAULT_TARGETED_POSITION_TREE)
  assert.deepEqual(recovered, tree)
  assert.deepEqual(store.positionTree, tree)
  assert.equal(store.positionsLoaded, true)
})
