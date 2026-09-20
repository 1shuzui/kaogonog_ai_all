const test = require('node:test')
const assert = require('node:assert/strict')
const { createNavigator } = require('../src/custom-tab-bar/navigation.cjs')

function fixture(route = 'a') {
  const requests = []
  let actual = route
  const nav = createNavigator({
    readRoute: () => actual,
    navigate: (target, done) => requests.push({ target, done }),
    notify: () => {}
  })
  return { nav, requests, finish(i, success = true) {
    if (success) actual = requests[i].target
    requests[i].done(success)
  } }
}

test('direct entry uses the real route, repeating current tab is a no-op', () => {
  const { nav, requests } = fixture('c')
  assert.equal(nav.sync().confirmed, 'c')
  nav.request('c')
  assert.equal(requests.length, 0)
})

test('A → B → A preserves the last target while B is pending', () => {
  const f = fixture()
  f.nav.request('b'); f.nav.request('a')
  assert.equal(f.nav.snapshot().desired, 'a')
  f.finish(0)
  assert.deepEqual(f.requests.map(x => x.target), ['b', 'a'])
  f.finish(1)
  assert.equal(f.nav.snapshot().confirmed, 'a')
  assert.equal(f.nav.snapshot().pending, false)
})

test('A → B → C serializes navigation; repeated and old callbacks are harmless', () => {
  const f = fixture()
  f.nav.request('b'); f.nav.request('c'); f.nav.request('c')
  assert.equal(f.requests.length, 1)
  f.finish(0)
  assert.equal(f.requests.length, 2)
  f.finish(1)
  f.requests[0].done(false)
  assert.equal(f.nav.snapshot().confirmed, 'c')
  assert.equal(f.nav.snapshot().desired, 'c')
})

test('failure restores actual selection and allows retry; a newer target survives failure', () => {
  const f = fixture()
  f.nav.request('b'); f.finish(0, false)
  assert.equal(f.nav.snapshot().confirmed, 'a')
  assert.equal(f.nav.snapshot().desired, 'a')
  f.nav.request('b'); f.nav.request('c'); f.finish(1, false)
  assert.equal(f.requests[2].target, 'c')
  f.finish(2)
  assert.equal(f.nav.snapshot().confirmed, 'c')
})

test('lifecycle sync is idempotent and never consumes a queued return target', () => {
  const f = fixture()
  f.nav.request('b'); f.nav.request('a')
  const request = f.nav.snapshot().requestId
  f.nav.sync(); f.nav.sync()
  assert.equal(f.nav.snapshot().requestId, request)
  assert.equal(f.nav.snapshot().desired, 'a')
  f.finish(0); f.finish(1)
  f.nav.sync()
  assert.equal(f.requests.length, 2)
})
