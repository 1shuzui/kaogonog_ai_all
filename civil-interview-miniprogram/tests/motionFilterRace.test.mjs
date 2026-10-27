import test from 'node:test'
import assert from 'node:assert/strict'
import { effectScope, nextTick, ref } from 'vue'
import { useFullExamSelection } from '../src/composables/useFullExamSelection.mjs'

function fixture(t) {
  const requests = []
  const scope = effectScope()
  t.after(() => scope.stop())
  const targetFilterParams = ref({ province: 'jiangsu' })
  const hasFullAccess = ref(true)
  const selection = scope.run(() => useFullExamSelection({
    targetFilterParams, hasFullAccess,
    loadSuites: filters => new Promise((resolve, reject) => requests.push({ filters, resolve, reject }))
  }))
  return { ...selection, requests, targetFilterParams, hasFullAccess }
}

test('rapid filter reversal retains the latest suite list, not a slow previous response', async t => {
  const f = fixture(t)
  const first = f.refreshFullExamSuites(); const latest = f.refreshFullExamSuites()
  f.requests[1].resolve([{ id: 'latest' }]); await latest
  f.requests[0].resolve([{ id: 'stale' }]); await first
  assert.deepEqual(f.fullExamSuites.value.map(suite => suite.id), ['latest'])
})

test('a stale error cannot clear the new list or stop the latest loading state', async t => {
  const f = fixture(t)
  const first = f.refreshFullExamSuites(); const latest = f.refreshFullExamSuites()
  f.requests[0].reject(new Error('stale')); await first
  assert.equal(f.fullExamSuitesLoading.value, true)
  assert.equal(f.fullExamSuitesError.value, '')
  f.requests[1].resolve([{ id: 'latest' }]); await latest
  assert.equal(f.fullExamSuitesLoading.value, false)
})

test('scope changes synchronously clear selection and failed loads can be retried', async t => {
  const f = fixture(t)
  const initial = f.refreshFullExamSuites()
  f.requests[0].resolve([{ id: 'old' }]); await initial; await nextTick()
  assert.equal(f.selectedFullExamSuite.value.id, 'old')
  f.targetFilterParams.value = { province: 'anhui', examTrack: 'institution' }
  assert.equal(f.selectedFullExamSuite.value, null)
  assert.equal(f.loadedFullExamScope.value, '')
  assert.equal(f.fullExamSuitesLoading.value, true)
  f.requests[1].reject(new Error('offline')); await nextTick(); await nextTick()
  assert.equal(f.fullExamSuitesError.value, 'offline')
  const retry = f.refreshFullExamSuites()
  f.requests[2].resolve([{ id: 'new' }]); await retry
  assert.equal(f.fullExamSuitesError.value, '')
  assert.equal(f.loadedFullExamScope.value, JSON.stringify(f.targetFilterParams.value))
  assert.equal(f.selectedFullExamSuite.value.id, 'new')
})

test('disposed selection ignores late successes and failures', async t => {
  const f = fixture(t)
  const first = f.refreshFullExamSuites(); const latest = f.refreshFullExamSuites()
  f.dispose()
  f.requests[0].reject(new Error('late')); f.requests[1].resolve([{ id: 'late' }])
  await Promise.all([first, latest])
  assert.deepEqual(f.fullExamSuites.value, [])
  assert.equal(f.loadedFullExamScope.value, '')
  assert.equal(f.fullExamSuitesError.value, '')
})

test('without full access refresh clears old state and does not request suites', async t => {
  const f = fixture(t)
  const initial = f.refreshFullExamSuites()
  f.requests[0].resolve([{ id: 'old' }]); await initial
  f.hasFullAccess.value = false
  await f.refreshFullExamSuites()
  assert.equal(f.requests.length, 1)
  assert.equal(f.selectedFullExamSuite.value, null)
  assert.equal(f.fullExamSuitesLoading.value, false)
  assert.equal(f.loadedFullExamScope.value, '')
})
