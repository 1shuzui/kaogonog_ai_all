import test from 'node:test'
import assert from 'node:assert/strict'
import vm from 'node:vm'
import { readFileSync } from 'node:fs'
import { computed, ref, reactive, watch, nextTick } from 'vue'
import { createPinia, defineStore } from 'pinia'
import { parse, compileScript, compileTemplate } from '@vue/compiler-sfc'
import * as constants from '../src/utils/constants.js'
import { JIANGSU_TARGETED_POSITIONS } from '../src/utils/jiangsuJobs.js'
import { normalizeListResponse } from '../src/utils/format.js'
import * as practiceSelection from '../../shared/practiceSelection.mjs'

const source = readFileSync(new URL('../src/pages/bank/index.vue', import.meta.url), 'utf8')
const { descriptor } = parse(source)
const plain = value => JSON.parse(JSON.stringify(value))
const bindingNames = ['selectedProvince', 'selectedProvinceName', 'provinceOptions', 'examCategoryFilter', 'examCategoryOptions', 'selectedDimension', 'dimensionOptions', 'subcategoryFilter', 'subcategory2Filter', 'subcategoryLabel', 'subcategoryOptions', 'subcategory2Options', 'yearFilter', 'yearDraft', 'yearOptions', 'unavailableYears', 'showYearPicker', 'showAdvancedFilters', 'categoryReviewFilter', 'selectedPosition', 'keyword', 'filterSummary', 'pageError', 'buildFilters', 'onFilterChange', 'onProvinceChange', 'onExamCategoryChange', 'onDimensionChange', 'onPositionChange', 'onYearChange', 'onSubcategoryChange', 'onSubcategory2Change', 'openYearPicker', 'applyYearDraft', 'resetFilters', 'goPage', 'retryQuestions', 'retryFilterOptions', 'goEdit', 'goAdd', 'goImport', 'startRandomPractice']

async function page({ paid = true, token = 'account-a', failList = false, filters = {}, loadUserInfo = async () => {}, bankStore = null } = {}) {
  const requests = [], metadataRequests = [], navigations = []
  let onShow
  const stops = []
  const user = reactive({ token, isAdmin: false, selectedProvince: 'jiangsu', provinces: constants.PROVINCES, loadProvinces: async () => {}, loadUserInfo })
  const access = ref(paid)
  const metadata = {
    options: ref({ year: ['2026', '2016'], subcategory: ['盐城市'], subcategory2: ['东台'] }),
    loading: ref(false), error: ref(''), questionCount: ref(3),
    refresh: async (params, enabled) => {
      metadataRequests.push({ params: plain(params), enabled })
      if (!enabled) metadata.options.value = { year: [], subcategory: [], subcategory2: [] }
    }
  }
  const bank = bankStore || reactive({
    questions: [], loading: false, error: '',
    filtersInitialized: Object.keys(filters).length > 0,
    filters: { keyword: '', province: 'national', dimension: '', examCategory: '', subcategory: '', subcategory2: '', year: '', position: '', ...filters },
    pagination: { current: 1, pageSize: 10, total: 0 },
    setFilters(value) { this.filtersInitialized = true; this.filters = { ...this.filters, ...value }; this.pagination.current = 1 },
    async fetchQuestions(params) {
      requests.push(plain({ ...this.filters, ...params }))
      if (failList) { this.error = 'offline'; throw new Error('offline') }
      this.questions = [{ id: 'q1' }]
    },
    fetchRandom: async params => { requests.push(plain(params)); return [{ id: 'q&1' }] },
    $reset() { this.questions = []; this.pagination.total = 0; this.loading = false; this.error = '' }
  })
  const mocks = {
    '../../../../shared/practiceSelection.mjs': practiceSelection,
    vue: { computed, ref, watch: (...args) => { const stop = watch(...args); stops.push(stop); return stop } },
    '@dcloudio/uni-app': { onShow: fn => { onShow = fn } },
    '../../motion/useMotion': { usePageMotion: () => ({ motionClass: '', motionStyle: {} }) },
    '../../api/questionBank': { importDocx: async () => ({ imported: 1 }) },
    '../../stores/billing': { useBillingStore: () => ({}) },
    '../../stores/questionBank': { useQuestionBankStore: () => bank },
    '../../stores/subscription': { useSubscriptionStore: () => ({ refresh: async () => {} }) },
    '../../stores/user': { useUserStore: () => user },
    '../../utils/access': { hasPremiumAccess: () => access.value },
    '../../utils/constants': constants,
    '../../utils/jiangsuJobs': { JIANGSU_TARGETED_POSITIONS },
    '../../utils/useQuestionFilters': { useQuestionFilters: () => metadata },
    '../../utils/navigation': { hasToken: () => !!user.token, promptLoginForAction: () => !!user.token, hideLoading() {}, showLoading() {}, toast() {} }
  }
  const context = vm.createContext({ uni: { navigateTo: ({ url }) => navigations.push(url) } })
  const exports = [...bindingNames, 'pageLoading'].map(name => `${name}: typeof ${name} === 'undefined' ? undefined : ${name}`).join(',')
  const module = new vm.SourceTextModule(`${descriptor.scriptSetup.content}\nexport const bindings = {${exports}}`, { context })
  await module.link(name => {
    const values = name.endsWith('.vue') ? { default: {} } : mocks[name]
    assert.ok(values, `missing dependency ${name}`)
    return new vm.SyntheticModule(Object.keys(values), function () {
      for (const [key, value] of Object.entries(values)) this.setExport(key, value)
    }, { context })
  })
  await module.evaluate()
  return { ...module.namespace.bindings, bank, user, access, metadata, requests, metadataRequests, navigations, show: () => onShow(), stop: () => stops.forEach(stop => stop()) }
}

async function realBank() {
  const requests = []
  const context = vm.createContext({})
  const module = new vm.SourceTextModule(readFileSync(new URL('../src/stores/questionBank.js', import.meta.url), 'utf8'), { context })
  const imports = {
    pinia: { defineStore },
    '../api/questionBank': {
      getQuestions: params => new Promise((resolve, reject) => requests.push({ params, resolve, reject })),
      deleteQuestion() {}, getQuestionById() {}, getRandomQuestions() {}
    },
    '../utils/format': { normalizeListResponse }
  }
  await module.link(name => new vm.SyntheticModule(Object.keys(imports[name]), function () {
    for (const [key, value] of Object.entries(imports[name])) this.setExport(key, value)
  }, { context }))
  await module.evaluate()
  const bank = module.namespace.useQuestionBankStore(createPinia())
  return { bank, requests }
}

async function flushUntil(predicate) {
  // Bounded microtasks, no timers or SDK. Deferred network requests stay pending.
  for (let turn = 0; turn < 30 && !predicate(); turn += 1) await Promise.resolve()
  assert.ok(predicate(), 'expected async boundary was not reached')
}

for (const oldOutcome of ['success', 'failure']) {
  test(`real page + store: Shandong releases the UI while onShow A hangs (late A ${oldOutcome})`, async () => {
    const { bank, requests } = await realBank()
    const p = await page({ bankStore: bank })
    let oldShowFinished = false
    const showing = p.show().then(() => { oldShowFinished = true })
    try {
      await flushUntil(() => requests.length === 1)
      assert.equal(requests[0].params.province, 'jiangsu')
      p.onProvinceChange({ detail: { value: p.provinceOptions.value.findIndex(item => item.code === 'shandong') } })
      assert.equal(requests[1].params.province, 'shandong')
      requests[1].resolve({ list: [{ id: 'shandong-latest' }], total: 25 })
      await flushUntil(() => !bank.loading)
      assert.equal(oldShowFinished, false, 'A must remain pending until after all UI assertions')
      assert.deepEqual(Array.from(bank.questions, item => item.id), ['shandong-latest'])
      assert.equal(bank.error, '')
      assert.equal(p.pageLoading.value, false, 'old onShow must not keep the successful new list in loading state')
      assert.equal(bank.pagination.current >= Math.ceil(bank.pagination.total / bank.pagination.pageSize), false, 'next page exists')
      // These are the real page template conditions, not a second copy of UI logic.
      const ui = { bankStore: bank, pageLoading: p.pageLoading.value, totalPages: Math.ceil(bank.pagination.total / bank.pagination.pageSize) }
      const staleHintCondition = source.match(/<text v-if="([^"]+)" class="filter-help">以下保留上次成功加载/)[1]
      const nextPageDisabled = source.match(/<button[^>]*:disabled="([^"]+)"[^>]*@tap="goPage\(bankStore.pagination.current \+ 1\)"/)[1]
      assert.equal(Boolean(vm.runInNewContext(staleHintCondition, ui)), false)
      assert.equal(Boolean(vm.runInNewContext(nextPageDisabled, ui)), false)
    } finally {
      if (requests[0]) {
        if (oldOutcome === 'success') requests[0].resolve({ list: [{ id: 'jiangsu-stale' }], total: 99 })
        else requests[0].reject(new Error('obsolete Jiangsu request'))
      }
      await showing
      p.stop()
      bank.$dispose()
    }
    assert.equal(p.pageLoading.value, false)
    assert.deepEqual(Array.from(bank.questions, item => item.id), ['shandong-latest'])
    assert.equal(bank.error, '')
  })
}

test('real page + store: old list finally cannot release a newer onShow initialization', async () => {
  const { bank, requests } = await realBank()
  let profiles = 0, finishNewProfile
  const p = await page({ bankStore: bank, loadUserInfo: () => ++profiles === 1 ? Promise.resolve() : new Promise(resolve => { finishNewProfile = resolve }) })
  const firstShow = p.show()
  await flushUntil(() => requests.length === 1)
  const latestShow = p.show()
  assert.equal(p.pageLoading.value, true)
  requests[0].resolve({ list: [{ id: 'first' }], total: 25 })
  await firstShow
  assert.equal(p.pageLoading.value, true, 'the new profile initialization still owns pageLoading')
  finishNewProfile()
  await flushUntil(() => requests.length === 2)
  try {
    assert.equal(p.pageLoading.value, false, 'initialization hands off to the latest store request')
    assert.equal(bank.loading, true, 'the pending current list still owns its loading state')
  } finally {
    requests[1].resolve({ list: [{ id: 'latest' }], total: 25 })
    await latestShow
    p.stop()
    bank.$dispose()
  }
})

test('onShow uses one visible filter snapshot for the first list and metadata request', async () => {
  const p = await page()
  await p.show()
  assert.equal(p.selectedProvince.value, 'jiangsu')
  assert.equal(p.requests[0].province, 'jiangsu')
  assert.equal(p.metadataRequests[0].params.province, 'jiangsu')
  assert.equal(p.metadataRequests[0].enabled, true)
})

test('onShow preserves all cached controls, including an explicit all-regions value', async () => {
  const filters = { province: '', keyword: '校园', dimension: 'analysis', examCategory: '事业单位考试', subcategory: '盐城市', subcategory2: '东台', year: '2016,2026' }
  const p = await page({ filters })
  await p.show()
  for (const [key, value] of Object.entries(filters)) assert.equal(p.requests[0][key], value, key)
})

test('an in-flight onShow keeps a newly selected province in both requests', async () => {
  let finishProfile
  const p = await page({ loadUserInfo: () => new Promise(resolve => { finishProfile = resolve }) })
  const showing = p.show()
  p.onProvinceChange({ detail: { value: p.provinceOptions.value.findIndex(item => item.code === 'shandong') } })
  finishProfile(); await showing
  assert.equal(p.selectedProvince.value, 'shandong')
  assert.ok(p.requests.every(request => request.province === 'shandong'))
  assert.ok(p.metadataRequests.every(request => request.params.province === 'shandong'))
  p.stop()
})

test('onShow and profile failures stay navigable and do not reject', async () => {
  const p = await page({ failList: true, loadUserInfo: async () => { throw new Error('profile offline') } })
  await assert.doesNotReject(p.show())
  assert.equal(p.bank.error, 'offline')
  assert.match(p.pageError.value, /重试/)
  p.goImport()
  assert.equal(p.navigations.at(-1), '/pages/admin/import')
  p.stop()
})

test('onShow that finishes after an account ABA cannot refetch protected data', async () => {
  let finishProfile
  const p = await page({ loadUserInfo: () => new Promise(resolve => { finishProfile = resolve }) })
  const showing = p.show()
  p.user.token = 'account-b'
  p.user.token = 'account-a'
  finishProfile(); await showing
  assert.equal(p.requests.length, 0)
  assert.ok(p.metadataRequests.every(request => !request.enabled))
  p.stop()
})

test('metadata retries and summary use the submitted keyword, not unsubmitted search text', async () => {
  const p = await page()
  p.keyword.value = '  已搜索  '
  await p.onFilterChange()
  p.keyword.value = '尚未搜索'
  await p.retryFilterOptions()
  assert.equal(p.metadataRequests.at(-1).params.keyword, '已搜索')
  assert.match(p.filterSummary.value, /已搜索/)
  assert.doesNotMatch(p.filterSummary.value, /尚未搜索/)
  p.stop()
})

test('metadata receives base plus classifications, never selected year or admin review', async () => {
  const p = await page()
  p.keyword.value = '  校园  '; p.selectedDimension.value = 'analysis'
  p.examCategoryFilter.value = '事业单位考试'; p.selectedPosition.value = 'jiangsu_e'
  p.subcategoryFilter.value = '盐城市'; p.subcategory2Filter.value = '东台'
  p.yearFilter.value = ['2026']; p.categoryReviewFilter.value = 'needs_review'
  await p.onFilterChange()
  assert.deepEqual(p.metadataRequests.at(-1).params, {
    province: 'jiangsu', dimension: 'analysis', position: 'jiangsu_e', keyword: '校园',
    examCategory: '事业单位考试', subcategory: '盐城市', subcategory2: '东台', year: ''
  })
  assert.equal(p.requests.at(-1).year, '2026')
  assert.equal(p.requests.at(-1).categoryReview, 'needs_review')
  p.stop()
})

test('list failures are awaited and caught by search and pagination for inline display', async () => {
  const p = await page({ failList: true })
  await assert.doesNotReject(p.onFilterChange())
  assert.equal(p.bank.error, 'offline')
  await assert.doesNotReject(p.goPage(2))
  assert.equal(p.bank.error, 'offline')
  assert.equal(p.requests.at(-1).current, 2)
})

test('year options are only metadata; draft selection applies once across repeated close events', async () => {
  const p = await page()
  p.yearFilter.value = ['2016']
  assert.deepEqual(Array.from(p.yearOptions.value, option => option.value), ['2026', '2016'])
  p.openYearPicker()
  p.onYearChange({ detail: { value: ['2026', '2016'] } })
  assert.deepEqual(Array.from(p.yearFilter.value), ['2016'])
  assert.equal(p.requests.length, 0)
  await p.applyYearDraft()
  await p.applyYearDraft()
  assert.deepEqual(Array.from(p.yearFilter.value), ['2026', '2016'])
  assert.equal(p.requests.length, 1)
  assert.equal(p.requests[0].year, '2026,2016')
})

test('removed choices remain selected, are identified as unavailable and never injected as available', async () => {
  const p = await page()
  p.yearFilter.value = ['1998']
  p.subcategoryFilter.value = '已移除分类'
  p.openYearPicker()
  assert.deepEqual(Array.from(p.yearOptions.value, option => option.value), ['2026', '2016'])
  assert.deepEqual(Array.from(p.unavailableYears.value), ['1998'])
  assert.ok(!p.subcategoryOptions.value.some(option => option.value === '已移除分类'))
  await p.applyYearDraft()
  assert.deepEqual(Array.from(p.yearFilter.value), ['1998'])
  assert.equal(p.subcategoryFilter.value, '已移除分类')
  assert.equal(p.requests.length, 0, 'unchanged draft should not fetch')
})

test('year changes preserve removed selections until explicitly cleared', async () => {
  const p = await page()
  p.yearFilter.value = ['1998']
  p.openYearPicker()
  p.onYearChange({ detail: { value: ['2026'] } })
  await p.applyYearDraft()
  assert.deepEqual(Array.from(p.yearFilter.value), ['1998', '2026'])
  p.openYearPicker()
  p.yearDraft.value = []
  await p.applyYearDraft()
  assert.equal(p.requests.at(-1).year, '')
  assert.equal(p.requests.length, 2)
  p.stop()
})

test('classification labels follow the real exam system and dependent controls use actual options', async () => {
  const p = await page()
  p.examCategoryFilter.value = '事业单位考试'
  assert.equal(p.subcategoryLabel.value, '地级市')
  p.onSubcategoryChange({ detail: { value: 1 } })
  assert.equal(p.subcategoryFilter.value, '盐城市')
  p.onSubcategory2Change({ detail: { value: 1 } })
  assert.equal(p.subcategory2Filter.value, '东台')
  assert.ok(p.examCategoryOptions.value.filter(option => option.code === '').length === 1)
  assert.ok(p.dimensionOptions.value.filter(option => option.key === '').length === 1)
  p.selectedProvince.value = 'national'
  assert.equal(p.selectedProvinceName.value, '全国题源')
})

test('reset clears every query filter and metadata has the same base/classification snapshot', async () => {
  const p = await page()
  p.keyword.value = 'foo'; p.selectedPosition.value = 'jiangsu_e'
  p.subcategoryFilter.value = '盐城市'; p.subcategory2Filter.value = '东台'
  p.yearFilter.value = ['2026']; p.categoryReviewFilter.value = 'needs_review'
  await p.resetFilters()
  for (const value of Object.values(p.buildFilters())) assert.equal(value, '')
  assert.equal(p.requests.length, 1)
  assert.equal(p.metadataRequests.length, 1)
  assert.equal(p.metadataRequests[0].params.province, '')
})

test('anonymous and unpaid onShow do not query list or paid metadata', async () => {
  for (const options of [{ token: '' }, { paid: false }]) {
    const p = await page(options)
    await p.show()
    assert.equal(p.requests.length, 0)
    assert.ok(p.metadataRequests.every(request => !request.enabled))
    p.stop()
  }
})

test('account/access loss disables metadata before clearing protected content', async () => {
  const p = await page()
  await p.show()
  p.access.value = false
  await nextTick()
  assert.equal(p.metadataRequests.at(-1).enabled, false)
  assert.equal(p.bank.questions.length, 0)
  p.stop()
})

test('admin navigation and random practice keep their handlers and exact parameters', async () => {
  const p = await page()
  p.goEdit({ id: 'a&b' }); p.goAdd(); p.goImport()
  assert.deepEqual(p.navigations, ['/pages/admin/question-edit?id=a%26b', '/pages/admin/question-edit', '/pages/admin/import'])
  p.keyword.value = '  校园  '
  await p.startRandomPractice()
  assert.equal(p.requests.at(-1).keyword, '校园')
  assert.equal(p.requests.at(-1).count, 1)
  const query = Object.fromEntries(new URL(`https://local${p.navigations.at(-1)}`).searchParams)
  assert.deepEqual(practiceSelection.readPracticeSelection(query).ids, ['q&1'])
  assert.equal(practiceSelection.readPracticeSelection(query).filters.keyword, '校园')
  assert.equal(practiceSelection.readPracticeSelection(query).filters.province, 'jiangsu')
})

test('bank template compiles with compact common filters, shared sheets, and native-size controls', () => {
  const script = compileScript(descriptor, { id: 'bank' })
  const compiled = compileTemplate({ source: descriptor.template.content, filename: 'bank.vue', id: 'bank', compilerOptions: { bindingMetadata: script.bindings } })
  assert.deepEqual(compiled.errors, [])
  assert.match(source, /<MotionCollapse[^>]*title="更多筛选"/)
  assert.match(source, /<LearnerSheet[^>]*close-label="完成"[^>]*@close="applyYearDraft"/)
  assert.match(source, /<LearnerSheet class="bank-year-sheet"/)
  assert.match(source, /细分方向/)
  assert.doesNotMatch(source, /YEAR_OPTIONS|三级分类|四级分类|v-model="subcategory(?:2)?Filter"|year-overlay/)
  assert.match(source, /min-height:\s*44px/)
  assert.match(source, /font-size:\s*14px/)
  assert.match(source, /var\(--ui-muted/)
  assert.ok(source.indexOf('title="考试类型"') < source.indexOf('title="更多筛选"'))
  assert.ok(source.indexOf('title="题型"') < source.indexOf('title="更多筛选"'))
})
