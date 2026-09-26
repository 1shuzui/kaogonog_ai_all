import test from 'node:test'
import assert from 'node:assert/strict'
import { createReviewStore } from '../reviewStore.mjs'

function fixture(api = {}, seed = {}) {
  const storage = new Map(Object.entries({ token: 'token-a', civil_user_id: '1', username: 'alice', ...seed }))
  const options = createReviewStore({ read: key => storage.get(key), write: (key, value) => storage.set(key, value), api })
  const store = Object.assign(options.state(), options.actions)
  for (const [name, getter] of Object.entries(options.getters)) Object.defineProperty(store, name, { get: () => getter(store) })
  return { storage, store }
}
const record = { id: 'a:q', examId: 'a', questionId: 'q', isWeak: false, isStarred: true }

test('account switch clears memory and anonymous scope never reads legacy favorites', async () => {
  const { storage, store } = fixture({ list: async () => ({ userId: '1', list: [record], total: 1 }) })
  assert.equal(await store.load(), true)
  assert.equal(store.count, 1)
  storage.set('civil_user_id', '2'); storage.set('token', 'token-b'); storage.set('username', 'bob')
  store.reloadForCurrentUser()
  assert.deepEqual(store.items, [])
  storage.delete('token'); storage.delete('civil_user_id')
  storage.set('civil_favorites', JSON.stringify([record]))
  store.reloadForCurrentUser()
  assert.deepEqual(store.items, [])
})

test('late responses cannot change another session or its persisted snapshot', async () => {
  let resolve, started
  const ready = new Promise(done => { started = done })
  const { storage, store } = fixture({ list: () => { started(); return new Promise(done => { resolve = done }) } })
  const pending = store.load()
  await ready
  storage.set('civil_user_id', '2'); storage.set('token', 'token-b'); storage.set('username', 'bob')
  store.reloadForCurrentUser()
  resolve({ userId: '1', list: [record], total: 1 })
  assert.equal(await pending, false)
  assert.equal(store.ownerId, '2')
  assert.deepEqual(store.items, [])
  assert.equal(storage.has('civil_reviews_v1:2'), false)
})

test('failed write retains server state and displays unsaved error', async () => {
  const { store } = fixture({
    list: async () => ({ userId: '1', list: [record], total: 1 }),
    update: async () => { throw new Error('服务暂时不可用') }
  })
  await store.load()
  assert.equal(await store.removeItem(record.id, 'starred'), false)
  assert.equal(store.count, 1)
  assert.match(store.error, /未保存.*服务暂时不可用/)
  assert.equal(store.saving, false)
})

test('migration only sends provenance and flags, keeps originals and does not rerun', async () => {
  let imports = 0
  const legacy = JSON.stringify([{ ...record, score: 900, questionStem: '不可信缓存' }])
  const { storage, store } = fixture({
    importItems: async items => {
      imports++
      assert.deepEqual(items, [{ examId: 'a', questionId: 'q', isStarred: true }])
      return { userId: '1', imported: 0, rejected: 1 }
    },
    list: async () => ({ userId: '1', list: [], total: 0 })
  }, { 'civil_favorites:alice': legacy })
  await store.load(); await store.load()
  assert.equal(imports, 1)
  assert.equal(storage.get('civil_favorites:alice'), legacy)
})

test('new client fails closed when response has a different owner', async () => {
  const { store } = fixture({ list: async () => ({ userId: '2', list: [record], total: 1 }) })
  assert.equal(await store.load(), false)
  assert.deepEqual(store.items, [])
})

test('switching accounts during refresh after a saved write cannot report success in the new session', async () => {
  let finish, started
  const ready = new Promise(done => { started = done })
  const { storage, store } = fixture({
    update: async () => ({ userId: '1' }),
    list: () => { started(); return new Promise(done => { finish = done }) }
  })
  const pending = store.addItem({ examId: 'a', questionId: 'q', type: 'starred' })
  await ready
  storage.set('civil_user_id', '2'); storage.set('token', 'token-b')
  store.reloadForCurrentUser()
  finish({ userId: '1', list: [record], total: 1 })
  assert.equal(await pending, false)
  assert.deepEqual(store.items, [])
  assert.equal(store.ownerId, '2')
  assert.equal(store.saving, false)
})
