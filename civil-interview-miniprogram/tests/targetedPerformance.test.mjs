import test from 'node:test'
import assert from 'node:assert/strict'
import vm from 'node:vm'
import { readFile } from 'node:fs/promises'
import * as contract from '../src/utils/targetedPerformance.mjs'
import { createCancellation } from '../src/utils/cancellation.mjs'
import { practiceQuery, readPracticeSelection, practiceFilterSummary } from '../../shared/practiceSelection.mjs'

const target = { province: 'jiangsu', examTrack: 'medical', year: ['2025', '2026'], positionTags: ['medical', '护理岗'], prepTime: 0 }
test('multi-value filters and zero timing survive fixed selection roundtrip', () => {
  const selection = readPracticeSelection(practiceQuery({ questionIds: ['q2', 'q1'], filters: target }))
  assert.deepEqual(selection.ids, ['q2', 'q1'])
  assert.deepEqual(selection.filters.year, target.year)
  assert.deepEqual(selection.filters.positionTags, target.positionTags)
  assert.equal(selection.filters.prepTime, '0')
  assert.match(practiceFilterSummary(selection.filters), /2025、2026/)
})
test('targeted practice defaults and route restore preserve complete scope', () => {
  const context = contract.practiceContext(target, '应急应变', 'recent30')
  assert.equal(context.mode, 'new')
  assert.equal(context.count, 3)
  const url = contract.targetedPracticeUrl(context)
  const query = Object.fromEntries(new URLSearchParams(url.split('?')[1]))
  assert.deepEqual(contract.readTargetedContext(query.targetedContext), context)
  assert.throws(() => contract.readTargetedContext('{broken'))
  assert.throws(() => contract.practiceContext(target, '逻辑结构', 'all'))
})
test('missing scores cannot masquerade as a successful empty report', () => {
  assert.throws(() => contract.validateReport({}))
  const report = { scopeKey: 's', analysisRevision: 'r', target, summary: {}, rules: { minSamples: 5, lowThreshold: 60, highThreshold: 80 },
    questionTypes: [{ questionType: '综合分析', sampleCount: 0, averagePercent: null }] }
  assert.equal(contract.validateReport(report), report)
  report.questionTypes[0].averagePercent = 0
  assert.throws(() => contract.validateReport(report))
})

async function fixture() {
  let token = 'alice'
  const pending = []
  const context = vm.createContext({ uni: { getStorageSync: () => token }, setTimeout, clearTimeout })
  const mocks = { pinia: { defineStore: (_, options) => options },
    '../api/targetedPerformance': { getPerformance: () => new Promise((resolve, reject) => pending.push({ resolve, reject })) },
    '../utils/targetedPerformance.mjs': contract, '../utils/cancellation.mjs': { createCancellation },
    '../utils/constants': { TOKEN_STORAGE_KEY: 'token' } }
  const module = new vm.SourceTextModule(await readFile(new URL('../src/stores/targetedPerformance.js', import.meta.url), 'utf8'), { context })
  await module.link(name => new vm.SyntheticModule(Object.keys(mocks[name]), function () {
    for (const [key, value] of Object.entries(mocks[name])) this.setExport(key, value)
  }, { context }))
  await module.evaluate()
  const options = module.namespace.useTargetedPerformanceStore
  const store = Object.assign(options.state(), options.actions)
  store.$reset = () => Object.assign(store, options.state())
  return { store, pending, switchAccount: () => { token = 'bob' } }
}
test('late old scope response cannot replace a new report', async () => {
  const { store, pending } = await fixture()
  store.setScope(target)
  const first = store.fetch()
  store.setScope({ ...target, province: 'anhui' })
  const next = store.fetch()
  pending[1].resolve({ id: 'new' }); await next
  pending[0].resolve({ id: 'old' }); await first
  assert.equal(store.report.id, 'new')
  assert.equal(store.status, 'success')
})
test('account switch clears returns and rejects late reports', async () => {
  const { store, pending, switchAccount } = await fixture()
  store.setScope(target)
  store.rememberExam('e1', contract.practiceContext(target, '综合分析', 'all'))
  const first = store.fetch()
  switchAccount()
  assert.equal(store.contextFor('e1'), null)
  store.setScope(target)
  pending[0].resolve({ id: 'old' }); await first
  assert.equal(store.report, null)
  assert.equal(store.contextFor('e1'), null)
})
test('same scope failure preserves dated report while changed scope clears it', async () => {
  const { store, pending } = await fixture()
  store.setScope(target)
  store.report = { updatedAt: 'saved-time' }
  const first = store.fetch()
  pending[0].reject(new Error('network')); await first
  assert.equal(store.status, 'error')
  assert.equal(store.report.updatedAt, 'saved-time')
  store.setScope(target, 'all')
  assert.equal(store.report, null)
})
