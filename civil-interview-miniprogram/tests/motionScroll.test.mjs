import test from 'node:test'
import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import vm from 'node:vm'
import { summaryState } from '../src/motion/policy.mjs'

test('an outstanding layout measurement never rolls back a newer scroll event', async () => {
  const queries = []; let show
  const query = { in() { return this }, select() { return this }, boundingClientRect() { return this }, selectViewport() { return this }, scrollOffset() { return this }, exec(fn) { queries.push(fn) } }
  const context = vm.createContext({ uni: { createSelectorQuery: () => query } })
  const source = readFileSync(new URL('../src/motion/useScrollSummary.js', import.meta.url), 'utf8')
  const module = new vm.SourceTextModule(source, { context })
  const imports = {
    vue: { getCurrentInstance: () => ({ proxy: {} }), nextTick: () => Promise.resolve(), ref: value => ({ value }), watch() {} },
    '@dcloudio/uni-app': { onReady() {}, onResize() {}, onShow(fn) { show = fn }, onHide() {}, onUnload() {} },
    './policy.mjs': { summaryState },
    './tokens.json': { default: { summaryHysteresisPx: 20, summaryHeightPx: 48 } }
  }
  await module.link(name => new vm.SyntheticModule(Object.keys(imports[name]), function() {
    for (const [key, value] of Object.entries(imports[name])) this.setExport(key, value)
  }, { context }))
  await module.evaluate()
  const summary = module.namespace.useScrollSummary('.hero')
  show(); await new Promise(resolve => setImmediate(resolve))
  queries[0]([{ bottom: 248 }, { scrollTop: 0 }])
  await summary.calibrate()
  summary.onSummaryScroll({ scrollTop: 250 })
  assert.equal(summary.compact.value, true)
  queries[1]([{ bottom: 248 }, { scrollTop: 0 }])
  assert.equal(summary.compact.value, true)
})
