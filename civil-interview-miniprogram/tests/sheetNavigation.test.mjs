import test from 'node:test'
import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import vm from 'node:vm'
import { holdSheetNavigation } from '../src/utils/sheetNavigation.mjs'

test('each sheet owns a page-local, idempotently released navigation hold', () => {
  const states = [], page = { getTabBar: () => ({ setSheetOpen: open => states.push(open) }) }
  const first = holdSheetNavigation(page), second = holdSheetNavigation(page)
  first(); first()
  assert.equal(page.__learnerSheetCount, 1)
  assert.equal(states.at(-1), true)
  second()
  assert.equal(page.__learnerSheetCount, 0)
  assert.equal(states.at(-1), false)
})

test('a late component and a new page never reuse the previous tabBar instance', () => {
  const states = [], page = {}
  const release = holdSheetNavigation(page)
  assert.equal(page.__learnerSheetCount, 1)
  page.getTabBar = () => ({ setSheetOpen: open => states.push(open) })
  const nextPage = { __learnerSheetCount: 1 }
  release()
  assert.deepEqual(states, [false])
  assert.equal(nextPage.__learnerSheetCount, 1)
  assert.doesNotThrow(() => holdSheetNavigation(null)())
})

test('native tabBar syncs an already-open sheet on ready and blocks only modal navigation', () => {
  let definition, requests = 0
  const page = { route: 'pages/home/index', __learnerSheetCount: 1 }
  vm.runInNewContext(readFileSync(new URL('../src/custom-tab-bar/index.js', import.meta.url), 'utf8'), {
    Component: value => { definition = value },
    getCurrentPages: () => [page],
    wx: { getWindowInfo: () => ({}), getStorageSync: () => 'off' },
    require: name => name === './navigation.js'
      ? { createNavigator: () => ({ sync: () => ({ confirmed: page.route }), request: () => requests++ }) }
      : name === './tabs.js' ? [{ pagePath: page.route }] : { defaultMode: 'off' }
  })
  const component = { data: { ...definition.data }, visible: true, setData(values) { Object.assign(this.data, values) }, ...definition.methods }
  component.syncRoute()
  assert.equal(component.data.sheetOpen, true)
  component.select({ currentTarget: { dataset: { index: 0 } } })
  assert.equal(requests, 0)
  component.setSheetOpen(false)
  component.select({ currentTarget: { dataset: { index: 0 } } })
  assert.equal(requests, 1)
  const wxml = readFileSync(new URL('../src/custom-tab-bar/index.wxml', import.meta.url), 'utf8')
  assert.match(wxml, /ready\s*&&\s*!sheetOpen/)
})
