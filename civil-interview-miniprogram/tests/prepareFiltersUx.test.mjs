import test from 'node:test'
import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import vm from 'node:vm'
import * as Vue from 'vue'
import { parse, compileScript } from '@vue/compiler-sfc'
import { QUESTION_CATEGORIES } from '../src/utils/constants.js'
import { DEFAULT_TARGETED_POSITION_TREE } from '../src/utils/targetedOptions.js'
import { normalizeProvinceCode } from '../src/utils/fullExamSuites.js'
import { createCancellation } from '../src/utils/cancellation.mjs'
import { readPracticeSelection, loadSelectedQuestions, practiceModeFor, practiceFilterSummary } from '../../shared/practiceSelection.mjs'

const pageSource = readFileSync(new URL('../src/pages/exam/prepare.vue', import.meta.url), 'utf8')
const { descriptor } = parse(pageSource)
const imports = compileScript(descriptor, { id: 'prepare-filters-test' }).scriptSetupAst
  .filter(node => node.type === 'ImportDeclaration')
const setupSource = [...imports].reverse().reduce(
  (source, node) => source.slice(0, node.start) + source.slice(node.end), descriptor.scriptSetup.content
)
const metadataSource = readFileSync(new URL('../src/utils/useQuestionFilters.js', import.meta.url), 'utf8')
  .replace(/^import .*$/gm, '').replace('export function', 'function')
const copy = value => JSON.parse(JSON.stringify(value))
const rows = [
  { id: 'analysis-js', province: 'jiangsu', dimension: 'analysis', year: '2026' },
  { id: 'emergency-js', province: 'jiangsu', dimension: 'emergency', year: '2024' },
  { id: 'analysis-ah', province: 'anhui', dimension: 'analysis', year: '2022' }
]

// Match get_question_filter_options/get_random_questions, not the unrelated
// _question_base_query: both current endpoints compare dimension by exact ==.
// A comma-joined selection is NOT split into multiple requests or treated as OR.
function matchingRows(params) {
  return rows.filter(row => (!params.province || params.province === 'all' || row.province === params.province)
    && (!params.dimension || row.dimension === params.dimension))
}

// Execute the real page setup, Vue watchers and metadata hook. Substitute only
// platform/store/API boundaries; never launch an SDK, write build output or hit a server.
async function fixture(t, options = {}) {
  const metadataRequests = [], questionRequests = [], notices = [], disposals = [], loads = [], starts = []
  const scope = Vue.effectScope()
  t.after(() => { disposals.forEach(dispose => dispose()); scope.stop() })
  const userStore = Vue.reactive({
    isAuthenticated: true, isAdmin: true, selectedProvince: 'jiangsu', preferences: {},
    loadUserInfo: async () => {}
  })
  const context = vm.createContext({
    ...Vue, console, setTimeout, clearTimeout, createCancellation,
    onBeforeUnmount: dispose => disposals.push(dispose),
    onLoad: callback => loads.push(callback), onShow() {}, onUnload: dispose => disposals.push(dispose),
    uni: { setNavigationBarTitle() {}, navigateTo() {} },
    usePageMotion: () => ({ motionClass: '', motionStyle: '' }),
    useUserStore: () => userStore,
    useTargetedStore: () => ({ generatedQuestions: options.cached || [] }),
    readPracticeSelection, loadSelectedQuestions, practiceModeFor, practiceFilterSummary,
    useBillingStore: () => ({}),
    useSubscriptionStore: () => ({ status: { canUse: true, remainingDailyMinutes: 10 }, refresh: async () => {} }),
    useExamStore: () => ({ setMediaMode() {}, startFromQuestions: async (questions, mode) => starts.push({ questions: copy(questions), mode }) }),
    getQuestionById: options.getQuestionById || (async id => ({ id, stem: id })),
    useQuestionBankStore: () => ({ fetchRandom: async params => {
      questionRequests.push(copy(params))
      return matchingRows(params)
    } }),
    getQuestionFilterOptions: async params => {
      metadataRequests.push(copy(params))
      const matched = matchingRows(params)
      return {
        options: { year: [...new Set(matched.map(row => row.year))].sort().reverse(), subcategory: [], subcategory2: [] },
        questionCount: matched.length
      }
    },
    hasPremiumAccess: () => true,
    requireLogin: () => true, showLoading() {}, hideLoading() {}, toast: message => notices.push(message),
    getAsrStatus: async () => ({ ready: true }),
    getQuestions: async () => [], requestFullExamSuites: async () => [], fetchFullExamSuites: async () => [],
    getFullExamSuiteSummary: () => '', normalizeProvinceCode,
    QUESTION_CATEGORIES, DEFAULT_TARGETED_POSITION_TREE
  })
  const page = scope.run(() => vm.runInContext(`${metadataSource}\n${setupSource}\n({
    count, yearOptions, filterMetadata, toggleQuestionType, onRegionFilterChange,
    onYearFilterChange, regionOptions, startPractice, selection, entryError
  })`, context))
  const settle = async () => { await Vue.nextTick(); await Vue.nextTick() }
  await settle()
  if (options.query) { loads.forEach(callback => callback(options.query)); await settle() }
  const start = async () => {
    const previous = questionRequests.length
    await page.startPractice()
    await settle()
    assert.equal(questionRequests.length, previous + 1, `Random query must run; notices: ${notices.join('; ')}`)
    return questionRequests.at(-1)
  }
  return { page, metadataRequests, questionRequests, notices, settle, start, starts }
}

test('changing question type refreshes metadata for the same scope as the actual random query', async t => {
  const f = await fixture(t)
  assert.equal(f.page.count.value, 5)
  assert.deepEqual(copy(f.page.yearOptions.value.map(option => option.value)), ['2026', '2024'])
  f.page.toggleQuestionType('analysis')
  await f.settle()
  assert.equal(f.metadataRequests.at(-1).dimension, 'analysis',
    'Metadata must refresh on selection, before the learner presses Start')
  const questionParams = await f.start()
  assert.equal(questionParams.dimension, 'analysis')
  assert.equal(f.metadataRequests.at(-1).dimension, questionParams.dimension,
    'Changing question type must invalidate the metadata scope, not leave the unfiltered years')
  assert.deepEqual(copy(f.page.yearOptions.value.map(option => option.value)), ['2026'])

  // The selected year is excluded from the year facet, even after a type change.
  f.page.onYearFilterChange({ detail: { value: ['2026'] } })
  await f.settle()
  assert.equal((await f.start()).year, '2026')
  assert.equal(f.metadataRequests.at(-1).year, '')
})

test('metadata uses the same saved-province fallback and explicit-region override as random practice', async t => {
  const f = await fixture(t)
  f.page.onRegionFilterChange({ detail: { value: 0 } })
  await f.settle()
  const fallback = await f.start()
  assert.equal(fallback.province, 'jiangsu')
  assert.equal(f.metadataRequests.at(-1).province, fallback.province,
    'Clearing the visible region must not broaden metadata while random practice still falls back to Jiangsu')
  assert.deepEqual(copy(f.page.yearOptions.value.map(option => option.value)), ['2026', '2024'])

  const anhuiIndex = f.page.regionOptions.value.findIndex(region => region.province === 'anhui')
  assert.ok(anhuiIndex >= 0)
  f.page.onRegionFilterChange({ detail: { value: anhuiIndex + 1 } })
  await f.settle()
  assert.equal((await f.start()).province, 'anhui')
  assert.equal(f.metadataRequests.at(-1).province, 'anhui')
  assert.deepEqual(copy(f.page.yearOptions.value.map(option => option.value)), ['2022'])
})

test('multiple types retain the joined exact-match value and honestly show empty metadata when no rows match', async t => {
  const f = await fixture(t)
  const previousMetadataRequests = f.metadataRequests.length
  f.page.toggleQuestionType('analysis')
  f.page.toggleQuestionType('emergency')
  await f.settle()
  const questionParams = await f.start()
  assert.equal(questionParams.dimension, 'analysis,emergency')
  assert.equal(f.questionRequests.length, 1, 'Do not fan out or widen the existing random-query contract')
  assert.equal(f.metadataRequests.at(-1).dimension, questionParams.dimension,
    'Metadata must receive the same joined value, not omit, split or intersect selected types')
  assert.equal(f.metadataRequests.length, previousMetadataRequests + 1,
    'A batched multi-type selection uses one metadata query, not per-type fan-out')
  assert.equal(f.page.filterMetadata.loading.value, false)
  assert.equal(f.page.filterMetadata.error.value, '')
  assert.deepEqual(copy(f.page.yearOptions.value), [], 'No fallback or unrelated years for an empty exact match')
  assert.ok(f.notices.includes('当前筛选条件暂无题目'))
})

test('explicit single question wins over a targeted group cached in the store', async t => {
  const f = await fixture(t, { query: { source: 'targeted', questionId: 'chosen' }, cached: [{ id: 'old-1' }, { id: 'old-2' }] })
  await f.page.startPractice()
  assert.deepEqual(f.starts.map(start => start.questions.map(q => q.id)), [['chosen']])
  assert.equal(f.starts[0].mode, 'targeted')
  assert.equal(f.questionRequests.length, 0)
})

test('ordered group is retained after a failed fetch and retry does not sample random questions', async t => {
  let fail = true
  const f = await fixture(t, {
    query: { source: 'targeted', questionIds: 'q3,q1,q5,q2,q4', filterSnapshot: JSON.stringify({ province: 'jiangsu', year: '2026' }) },
    getQuestionById: async id => { if (fail && id === 'q5') throw new Error('题目读取失败'); return { id, stem: id } }
  })
  await f.page.startPractice()
  assert.equal(f.starts.length, 0)
  assert.match(f.page.entryError.value, /选择已保留.*重试/)
  assert.deepEqual(copy(f.page.selection.value.ids), ['q3', 'q1', 'q5', 'q2', 'q4'])
  fail = false
  await f.page.startPractice()
  assert.deepEqual(f.starts[0].questions.map(q => q.id), ['q3', 'q1', 'q5', 'q2', 'q4'])
  assert.equal(f.starts[0].mode, 'targeted')
  assert.equal(f.questionRequests.length, 0)
})
