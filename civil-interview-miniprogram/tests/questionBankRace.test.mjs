import test from 'node:test'
import assert from 'node:assert/strict'
import vm from 'node:vm'
import { readFileSync } from 'node:fs'
import { createPinia, defineStore } from 'pinia'
import { normalizeListResponse } from '../src/utils/format.js'

// Execute the real store module and real Pinia state/reset behavior. Only I/O is deferred.
async function fixture() {
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
  const store = module.namespace.useQuestionBankStore(createPinia())
  return { store, requests }
}

const result = (ids, total = 30) => ({ list: ids.map(id => ({ id })), total })
const ids = store => Array.from(store.questions, item => item.id)
const settle = promise => promise.catch(() => {})

test('latest list wins when an older response arrives last', async () => {
  const { store, requests } = await fixture()
  const first = store.fetchQuestions({ province: 'jiangsu' })
  const latest = store.fetchQuestions({ province: 'shandong', current: 2 })
  requests[1].resolve(result(['latest'], 24)); await latest
  requests[0].resolve(result(['stale'], 99)); await first
  assert.deepEqual(ids(store), ['latest'])
  assert.equal(store.pagination.total, 24)
  assert.equal(store.pagination.current, 2)
})

for (const outcome of ['resolve', 'reject']) {
  test(`stale ${outcome} and finally cannot end the active request or set its error`, async () => {
    const { store, requests } = await fixture()
    const first = settle(store.fetchQuestions())
    const latest = store.fetchQuestions({ keyword: 'latest' })
    requests[0][outcome](outcome === 'resolve' ? result(['stale']) : new Error('old failure'))
    await first
    assert.equal(store.loading, true)
    assert.equal(store.error, '')
    requests[1].resolve(result(['latest'])); await latest
    assert.equal(store.loading, false)
  })
}

test('current failure preserves the last usable list and pagination and is cleared on retry', async () => {
  const { store, requests } = await fixture()
  store.questions = [{ id: 'usable' }]
  store.pagination = { current: 2, pageSize: 10, total: 42 }
  const failed = settle(store.fetchQuestions({ current: 3 }))
  requests[0].reject(new Error('network unavailable')); await failed
  assert.equal(store.error, 'network unavailable')
  assert.deepEqual(ids(store), ['usable'])
  assert.equal(store.pagination.current, 2)
  assert.equal(store.pagination.total, 42)
  assert.equal(store.loading, false)
  const retry = store.fetchQuestions({ current: 3 })
  assert.equal(store.error, '')
  requests[1].resolve(result(['recovered'])); await retry
  assert.deepEqual(ids(store), ['recovered'])
})

test('a stale success or failure cannot replace a newer failure', async () => {
  for (const outcome of ['resolve', 'reject']) {
    const { store, requests } = await fixture()
    store.questions = [{ id: 'usable' }]
    const old = settle(store.fetchQuestions())
    const latest = settle(store.fetchQuestions({ keyword: 'new' }))
    requests[1].reject(new Error('current failure')); await latest
    requests[0][outcome](outcome === 'resolve' ? result(['stale']) : new Error('stale failure'))
    await old
    assert.deepEqual(ids(store), ['usable'])
    assert.equal(store.error, 'current failure')
  }
})

test('old append cannot contaminate a new filtered list', async () => {
  const { store, requests } = await fixture()
  store.questions = [{ id: 'old-page-1' }]
  const more = store.fetchMore({ current: 2 })
  store.setFilters({ province: 'shandong' })
  const latest = store.fetchQuestions({ current: 1 })
  requests[1].resolve(result(['new-page-1'])); await latest
  requests[0].resolve(result(['old-page-2'])); await more
  assert.deepEqual(ids(store), ['new-page-1'])
  assert.equal(store.pagination.current, 1)
})

test('an old replacement cannot overwrite the current append and append still deduplicates', async () => {
  const { store, requests } = await fixture()
  store.questions = [{ id: 'one' }]
  const old = store.fetchQuestions()
  const more = store.fetchMore({ current: 2 })
  requests[1].resolve(result(['one', 'two'])); await more
  requests[0].resolve(result(['stale'])); await old
  assert.deepEqual(ids(store), ['one', 'two'])
  assert.equal(store.pagination.current, 2)
})

test('overlapping append responses only commit the newest request', async () => {
  const { store, requests } = await fixture()
  store.questions = [{ id: 'one' }]
  const older = store.fetchMore({ current: 2 })
  const latest = store.fetchMore({ current: 2 })
  requests[1].resolve(result(['two'])); await latest
  requests[0].resolve(result(['stale-two'])); await older
  assert.deepEqual(ids(store), ['one', 'two'])
})

for (const method of ['fetchQuestions', 'fetchMore']) {
  test(`${method}: $reset alone rejects late success and failure without resurrecting state`, async () => {
    for (const outcome of ['resolve', 'reject']) {
      const { store, requests } = await fixture()
      store.questions = [{ id: 'old' }]
      const pending = settle(store[method]())
      store.$reset()
      requests[0][outcome](outcome === 'resolve' ? result(['stale']) : new Error('stale'))
      await pending
      assert.deepEqual(ids(store), [])
      assert.equal(store.pagination.total, 0)
      assert.equal(store.loading, false)
      assert.equal(store.error, '')
    }
  })

  test(`${method}: $reset invalidates in-flight work, including ABA after another request`, async () => {
    const { store, requests } = await fixture()
    store.questions = [{ id: 'old-account' }]
    const old = settle(store[method]())
    store.$reset()
    const latest = store.fetchQuestions()
    requests[0].resolve(result(['old-account-late'])); await old
    assert.deepEqual(ids(store), [])
    assert.equal(store.loading, true)
    requests[1].resolve(result(['new-account'])); await latest
    assert.deepEqual(ids(store), ['new-account'])
  })

  test(`${method}: failure after reset cannot publish errors or end a new loading state`, async () => {
    const { store, requests } = await fixture()
    const old = settle(store[method]())
    store.$reset()
    const latest = store.fetchQuestions()
    requests[0].reject(new Error('old-account failure')); await old
    assert.equal(store.error, '')
    assert.equal(store.loading, true)
    requests[1].resolve(result([])); await latest
  })
}

test('current append failure preserves pages and an obsolete append failure is silent', async () => {
  const { store, requests } = await fixture()
  store.questions = [{ id: 'usable' }]
  store.pagination.total = 22
  const old = settle(store.fetchMore({ current: 2 }))
  const latest = settle(store.fetchMore({ current: 2 }))
  requests[0].reject(new Error('old append')); await old
  assert.equal(store.loading, true)
  assert.equal(store.error, '')
  requests[1].reject(new Error('current append')); await latest
  assert.equal(store.loading, false)
  assert.equal(store.error, 'current append')
  assert.deepEqual(ids(store), ['usable'])
  assert.equal(store.pagination.current, 1)
  assert.equal(store.pagination.total, 22)
})

test('changing filters without immediately fetching invalidates the previous request', async () => {
  const { store, requests } = await fixture()
  const old = store.fetchQuestions()
  store.setFilters({ keyword: 'next' })
  requests[0].resolve(result(['stale'])); await old
  assert.deepEqual(ids(store), [])
  assert.equal(store.loading, false)
})
