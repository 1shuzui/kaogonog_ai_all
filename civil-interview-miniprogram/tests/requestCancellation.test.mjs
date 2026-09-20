import test from 'node:test'
import assert from 'node:assert/strict'
import vm from 'node:vm'
import { readFile } from 'node:fs/promises'

async function setup() {
  const listeners = new Set(), calls = [], tips = []
  let aborts = 0, redirects = 0
  const signal = { aborted: false, subscribe(fn) { listeners.add(fn); return () => listeners.delete(fn) } }
  const cancel = () => { signal.aborted = true; for (const fn of [...listeners]) fn() }
  const context = vm.createContext({ setTimeout, clearTimeout, uni: {
    getStorageSync: () => 'session', removeStorageSync() {},
    request(options) { calls.push(options); return { abort() { aborts++; options.fail({ errMsg: 'request:fail abort' }) } } },
    reLaunch() { redirects++ }
  } })
  const mocks = {
    '../utils/constants': { TOKEN_STORAGE_KEY: 'token', USERNAME_STORAGE_KEY: 'user' },
    '../utils/navigation': { toast: value => tips.push(value) },
    '../utils/logger': { createRequestId: () => 'test', logger: { debug() {}, warn() {}, error() {} } }
  }
  const module = new vm.SourceTextModule(await readFile(new URL('../src/api/request.js', import.meta.url), 'utf8'), { context, initializeImportMeta(meta) { meta.env = { PROD: true } } })
  await module.link(name => new vm.SyntheticModule(Object.keys(mocks[name]), function () { for (const [key, value] of Object.entries(mocks[name])) this.setExport(key, value) }, { context }))
  await module.evaluate()
  return { request: module.namespace.request, signal, cancel, calls, listeners, tips, counts: () => ({ aborts, redirects }) }
}

test('cancel settles promptly, aborts only its request, and ignores late success/401/failure side effects', async () => {
  const api = await setup()
  const promise = api.request({ url: '/targeted/focus', signal: api.signal })
  const rejected = assert.rejects(promise, error => error.code === 'CANCELLED')
  api.cancel()
  // The baseline has no cancellation: explicitly deliver its failure to avoid a hanging red test.
  api.calls[0].fail({ errMsg: 'request:fail abort' })
  await rejected
  api.calls[0].success({ statusCode: 401, data: { detail: 'late' } })
  api.calls[0].success({ statusCode: 200, data: { questionCount: 10 } })
  assert.deepEqual(api.counts(), { aborts: 1, redirects: 0 })
  assert.deepEqual(api.tips, [])
  assert.equal(api.listeners.size, 0)
})

test('already cancelled signal does not issue a request; ordinary success releases its listener', async () => {
  const api = await setup()
  api.cancel()
  const pending = api.request({ url: '/targeted/focus', signal: api.signal })
  if (api.calls[0]) api.calls[0].fail({ errMsg: 'request:fail abort' })
  await assert.rejects(pending, error => error.code === 'CANCELLED')
  assert.equal(api.calls.length, 0)
  const next = await setup()
  const success = next.request({ url: '/positions', signal: next.signal })
  next.calls[0].success({ statusCode: 200, data: { tree: [] } })
  await success
  assert.equal(next.listeners.size, 0)
  next.cancel()
  assert.equal(next.counts().aborts, 0)
})
