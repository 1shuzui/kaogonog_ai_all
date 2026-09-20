import test from 'node:test'
import assert from 'node:assert/strict'
import vm from 'node:vm'
import { readFileSync } from 'node:fs'
const source = readFileSync(new URL('../src/pages/exam/prepare.vue', import.meta.url), 'utf8')
const declaration = source.match(/async function refreshFullExamSuites\([^]*?^}/m)[0]
const ref = value => ({ value })
function fixture() {
  const requests = [], errors = []
  const context = vm.createContext({ fullExamSuitesRequest: 0, hasFullAccess: ref(true), fullExamSuites: ref([]), selectedFullExamSuiteId: ref(''), fullExamSuitesLoading: ref(false), targetFilterParams: ref({ province: 'jiangsu' }), userStore: { selectedProvince: 'jiangsu' }, getQuestions() {}, requestFullExamSuites() {}, toast: msg => errors.push(msg), fetchFullExamSuites: () => new Promise((resolve, reject) => requests.push({ resolve, reject })) })
  const refresh = vm.runInContext(`(${declaration})`, context)
  return { context, refresh, requests, errors }
}
test('rapid filter reversal retains the latest suite list, not a slow previous response', async () => {
  const f = fixture()
  const first = f.refresh(); const latest = f.refresh()
  f.requests[1].resolve(['latest']); await latest
  f.requests[0].resolve(['stale']); await first
  assert.deepEqual(Array.from(f.context.fullExamSuites.value), ['latest'])
})
test('a stale error cannot clear the new list, show a toast or stop the latest loading state', async () => {
  const f = fixture()
  const first = f.refresh(); const latest = f.refresh()
  f.requests[0].reject(new Error('stale')); await first
  assert.equal(f.context.fullExamSuitesLoading.value, true)
  assert.deepEqual(f.errors, [])
  f.requests[1].resolve(['latest']); await latest
  assert.equal(f.context.fullExamSuitesLoading.value, false)
})
