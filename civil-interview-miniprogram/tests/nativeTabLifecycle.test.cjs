const test = require('node:test')
const assert = require('node:assert/strict')
const vm = require('node:vm')
const { readFileSync } = require('node:fs')
const { join } = require('node:path')
const { createNavigator } = require('../src/custom-tab-bar/navigation.cjs')
const tokens = require('../src/motion/tokens.json')

function fixture(initial = 4, mode = 'full') {
  const jobs = new Map(), requests = [], bars = [], routes = ['home', 'targeted', 'bank', 'training', 'profile'].map(name => `pages/${name}/index`)
  let definition, page, tick = 100, timer = 0
  const schedule = (fn, ms = 0) => { const id = ++timer; jobs.set(id, { fn, at: tick + ms }); return id }
  const cancel = id => jobs.delete(id)
  const advance = ms => {
    const until = tick + ms
    for (;;) {
      const next = [...jobs].filter(([, job]) => job.at <= until).sort((a, b) => a[1].at - b[1].at)[0]
      if (!next) break
      tick = next[1].at; jobs.delete(next[0]); next[1].fn()
    }
    tick = until
  }
  const setPage = index => { page = { route: routes[index], getTabBar: () => bars[index] } }
  setPage(initial)
  // The native runtime already owns this lexical name when ES6 re-transpilation is disabled.
  vm.runInNewContext('const navigator = { userAgent: "native-runtime" };\n' + readFileSync(join(__dirname, '../src/custom-tab-bar/index.js'), 'utf8'), {
    Component: value => { definition = value }, getCurrentPages: () => [page],
    setTimeout: schedule, clearTimeout: cancel, Date: { now: () => tick },
    wx: { getWindowInfo: () => ({}), getStorageSync: () => mode, switchTab: options => requests.push(options), showToast() {} },
    require: name => name === './navigation.js'
      ? { createNavigator: args => createNavigator({ ...args, schedule, cancel, now: () => tick }) }
      : name === './tabs.js' ? routes.map(pagePath => ({ pagePath })) : tokens
  })
  for (let i = 0; i < routes.length; i++) {
    bars.push({ data: { ...definition.data }, history: [], ...definition.methods,
      setData(values, callback) { Object.assign(this.data, values); this.history.push({ ...this.data }); callback?.() }
    })
    definition.lifetimes.attached.call(bars[i])
  }
  definition.lifetimes.ready.call(bars[initial])
  const tap = index => page.getTabBar().select({ currentTarget: { dataset: { index } } })
  const arrive = (index, callback = 'success') => {
    definition.pageLifetimes.hide.call(page.getTabBar())
    setPage(index)
    definition.pageLifetimes.show.call(bars[index])
    definition.lifetimes.ready.call(bars[index])
    if (callback) requests.at(-1)[callback]?.({ errMsg: 'switchTab:ok' })
  }
  return { bars, requests, tap, arrive, advance, ready() { definition.lifetimes.ready.call(page.getTabBar()) }, hide() { definition.pageLifetimes.hide.call(page.getTabBar()) }, show() { definition.pageLifetimes.show.call(page.getTabBar()) } }
}

test('the arriving native bar paints the previous tab, then slides to the real destination', () => {
  const f = fixture(4)
  f.tap(3)
  assert.equal(f.bars[4].data.visual, 4, 'do not animate twice across two native bars')
  f.arrive(3)
  assert.equal(f.bars[3].data.selected, 3)
  assert.equal(f.bars[3].data.visual, 4, 'start at the previous tab, never flash home')
  f.advance(32)
  assert.equal(f.bars[3].data.visual, 3)
  assert.equal(f.bars[3].data.moving, true)
  f.ready()
  assert.equal(f.bars[3].data.moving, true, 'late ready/show cannot cut off the animation')
})

test('a cached bar uses the latest transition on return instead of replaying an old selection', () => {
  const f = fixture(0)
  f.tap(3); f.arrive(3); f.advance(32)
  f.tap(2); f.arrive(2); f.advance(32)
  f.tap(3); f.arrive(3)
  assert.equal(f.bars[3].data.visual, 2)
  f.advance(32)
  assert.equal(f.bars[3].data.visual, 3)
})

test('hiding an arriving page cancels its pending animation frame', () => {
  const f = fixture(4)
  f.tap(0); f.arrive(0); f.hide(); f.advance(100)
  assert.equal(f.bars[0].data.ready, false)
  assert.equal(f.bars[0].data.moving, false)
  f.show()
  assert.equal(f.bars[0].data.visual, 0)
  assert.equal(f.bars[0].data.ready, true)
})

test('complete-only native callbacks release the queue and late callbacks are harmless', () => {
  const f = fixture(0)
  f.tap(3); f.tap(2); f.arrive(3, 'complete')
  assert.equal(f.requests.length, 2)
  f.arrive(2, 'complete'); f.requests[0].success({ errMsg: 'switchTab:ok' })
  f.advance(32)
  assert.equal(f.bars[2].data.selected, 2)
  f.tap(1)
  assert.equal(f.requests.length, 3)
})

test('login return without a tab request initializes the actual tab without a stale animation', () => {
  const f = fixture(4)
  f.hide(); f.show(); f.advance(100)
  assert.equal(f.bars[4].data.selected, 4)
  assert.equal(f.bars[4].data.visual, 4)
  assert.equal(f.bars[4].data.moving, false)
  f.tap(0); f.arrive(0); f.advance(32)
  assert.equal(f.bars[0].data.moving, true)
})

test('reduced and off modes switch normally without a delayed visual transition', () => {
  for (const mode of ['reduced', 'off']) {
    const f = fixture(4, mode)
    f.tap(0); f.arrive(0)
    assert.equal(f.bars[0].data.visual, 0)
    assert.equal(f.bars[0].data.moving, false)
  }
})
