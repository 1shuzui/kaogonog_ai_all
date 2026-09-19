import test from 'node:test'
import assert from 'node:assert/strict'
import { readFile } from 'node:fs/promises'
import vm from 'node:vm'

async function load(relative, mocks, globals = {}) {
  const context = vm.createContext({ ...globals, setTimeout: fn => fn() })
  const module = new vm.SourceTextModule(await readFile(new URL(relative, import.meta.url), 'utf8'), {
    context, initializeImportMeta(meta) { meta.env = { PROD: true } }
  })
  await module.link(name => {
    const exports = mocks[name]
    assert.ok(exports, `missing mock: ${name}`)
    return new vm.SyntheticModule(Object.keys(exports), function () {
      for (const [key, value] of Object.entries(exports)) this.setExport(key, value)
    }, { context })
  })
  await module.evaluate()
  return module.namespace
}

test('credential failures retain the active session; expired protected requests clear it', async () => {
  const storage = new Map([['token', 'old'], ['username', 'alice']])
  let pending, redirects = 0, logouts = 0
  const tips = []
  const uni = {
    getStorageSync: key => storage.get(key) || '',
    removeStorageSync: key => storage.delete(key),
    request: options => { pending = options },
    reLaunch: options => { redirects++; options.complete() }
  }
  const api = await load('../src/api/request.js', {
    '../utils/constants': { TOKEN_STORAGE_KEY: 'token', USERNAME_STORAGE_KEY: 'username' },
    '../utils/logger': { createRequestId: () => 'test', logger: { debug() {}, warn() {}, error() {} } },
    '../utils/navigation': { toast: message => tips.push(message) }
  }, { uni })
  api.setSessionExpiredHandler(() => { logouts++; storage.clear() })
  let promise = api.request({ url: '/token', authRequest: true, skipErrorHandler: true })
  pending.success({ statusCode: 401, data: { detail: '用户名或密码错误' } })
  await assert.rejects(promise, /用户名或密码错误/)
  assert.equal(logouts, 0)
  assert.equal(redirects, 0)
  assert.equal(storage.get('token'), 'old')

  for (const statusCode of [200, 401]) {
    promise = api.request({ url: '/history' })
    storage.set('token', `new-${statusCode}`)
    pending.success({ statusCode, data: { secret: 'old account data' } })
    await assert.rejects(promise, error => error.code === 'STALE_SESSION')
    assert.equal(logouts, 0)
  }
  promise = api.request({ url: '/user', skipErrorHandler: true })
  pending.success({ statusCode: 401, data: { detail: '账号已在其他同类客户端登录，请重新登录' } })
  await assert.rejects(promise, /同类客户端/)
  assert.equal(logouts, 1)
  assert.equal(redirects, 1)
  assert.match(tips.at(-1), /同类客户端/)
})

test('mini password login explicitly uses the WeChat session category', async () => {
  const api = await load('../src/api/auth.js', { './request': { request: options => options } })
  const result = api.login('test', 'pass&word')
  assert.equal(new URLSearchParams(result.data).get('client_type'), 'wechat')
  assert.equal(new URLSearchParams(result.data).get('password'), 'pass&word')
  assert.equal(result.authRequest, true)
})

for (const client of ['frontend', 'miniprogram']) {
  test(`${client}: training and billing caches do not leak across accounts`, async () => {
    const storage = new Map([['username', 'alice']])
    const read = key => storage.get(key) || ''
    const write = (key, value) => storage.set(key, value)
    storage.set('civil_training_progress', JSON.stringify({ legacy: { attempts: 100 } }))
    storage.set('civil_billing_state', JSON.stringify({ isPaid: true, orderHistory: ['legacy'] }))
    storage.set('civil_training_progress:alice', JSON.stringify({ analysis: { attempts: 3 } }))
    storage.set('civil_billing_state:alice', JSON.stringify({ isPaid: true, orderHistory: [{ id: 'alice-order' }] }))
    const mini = client === 'miniprogram'
    const logger = { warn() {} }
    const globals = { localStorage: { getItem: read, setItem: write }, uni: { getStorageSync: read, setStorageSync: write } }
    const mocks = {
      pinia: { defineStore: (_, options) => options },
      '@/utils/logger': { logger },
      '../api/training': { generateTrainingQuestions() {} },
      '../utils/constants': { TRAINING_PROGRESS_STORAGE_KEY: 'civil_training_progress', BILLING_STORAGE_KEY: 'civil_billing_state' }
    }
    // Web billing also imports its immutable plan constants.
    const billingCode = await readFile(new URL(`../../civil-interview-${client}/src/stores/billing.js`, import.meta.url), 'utf8')
    if (!mini) {
      for (const match of billingCode.matchAll(/import\s*\{([^}]+)\}\s*from\s*['"]([^'"]+)['"]/g)) {
        if (mocks[match[2]]) continue
        const constants = await import(new URL(`../../civil-interview-frontend/src/${match[2].replace('@/', '')}.js`, import.meta.url))
        mocks[match[2]] = Object.fromEntries(match[1].split(',').map(name => name.trim()).filter(Boolean).map(name => [name, constants[name]]))
      }
    }
    const training = await load(`../../civil-interview-${client}/src/stores/training.js`, mocks, globals)
    const billing = await load(`../../civil-interview-${client}/src/stores/billing.js`, mocks, globals)
    assert.equal(training.useTrainingStore.state().progress.analysis.attempts, 3)
    assert.equal(billing.useBillingStore.state().orderHistory[0].id, 'alice-order')
    storage.set('username', 'bob')
    assert.equal(Object.keys(training.useTrainingStore.state().progress).length, 0)
    assert.equal(billing.useBillingStore.state().orderHistory.length, 0)
  })
}
