import test from 'node:test'
import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import vm from 'node:vm'
import * as Vue from 'vue'
import { parse, compileScript, compileStyle } from '@vue/compiler-sfc'
import { compile as compileMiniTemplate } from '@dcloudio/uni-mp-compiler'
import { renderToString } from '@vue/server-renderer'
import * as constants from '../src/utils/constants.js'
import * as jiangsuJobs from '../src/utils/jiangsuJobs.js'
import * as targetedOptions from '../src/utils/targetedOptions.js'

const nativeTags = new Set(['view', 'text', 'button', 'input', 'checkbox', 'picker', 'scroll-view', 'navigator'])
const sourceOf = page => readFileSync(new URL(`../src/pages/${page}/index.vue`, import.meta.url), 'utf8')

// Run the actual page setup/render functions. Only native services and child
// components are substituted; no auth, network, timers or developer tools run.
async function pageFixture(page, { loggedIn = false, records = [], storedSections = {} } = {}) {
  const calls = [], hooks = {}, exposed = {}
  const storage = new Map([['civil_home_section_state', JSON.stringify(storedSections)]])
  const userStore = Vue.reactive({
    isAuthenticated: loggedIn, isAdmin: false, selectedProvince: 'jiangsu', selectedProvinceName: '江苏',
    provinces: [], preferences: { practicePreferenceConfirmed: true }, userInfo: {},
    loadUserInfo: async () => {}, loginWithWechat: async () => { calls.push('wechat'); return {} }
  })
  const historyStore = Vue.reactive({ records, stats: { totalExams: records.length }, trendData: [], averageScore: 80 })
  const genericComponent = { setup: (_, { slots }) => () => Vue.h('view', {}, slots.default?.()) }
  const collapseComponent = {
    props: ['open', 'title', 'revision'],
    setup: (props, { slots }) => () => Vue.h('view', {}, [
      props.title, slots.actions?.(), props.open ? slots.default?.() : null
    ])
  }
  const imports = {
    vue: Vue,
    '@dcloudio/uni-app': Object.fromEntries(['onShow', 'onLoad', 'onPageScroll', 'onPullDownRefresh'].map(name => [name, fn => { hooks[name] = fn }])),
    '../../motion/useMotion': { usePageMotion: () => ({ motionClass: '', motionStyle: '' }) },
    '../../motion/useScrollSummary': { useScrollSummary: () => ({ compact: Vue.ref(false), calibrate() {}, onSummaryScroll() {} }) },
    '../../stores/user': { useUserStore: () => userStore },
    '../../stores/history': { useHistoryStore: () => historyStore },
    '../../api/questionBank': { getRandomQuestions: async () => [] },
    '../../utils/navigation': {
      hasToken: () => loggedIn,
      promptLoginForAction: (action, url) => { calls.push({ action, url }); return loggedIn },
      toast: message => calls.push(message)
    },
    '../../utils/wechatLogin': { getWechatLoginCode: async () => 'test-code' },
    '../../utils/constants': constants,
    '../../utils/jiangsuJobs': jiangsuJobs,
    '../../utils/targetedOptions': targetedOptions,
    '../../utils/format': { formatDate: () => '9月20日' }
  }
  const names = page === 'home'
    ? 'sectionOpen, toggleSection, goPractice'
    : 'form, mode, loginByWechat, toggleAgreement, onAgreePrivacyAuthorization, accountSetupVisible'
  const { descriptor } = parse(sourceOf(page).replace('</script>', `defineExpose({ ${names} })\n</script>`), {
    templateParseOptions: { isCustomElement: tag => nativeTags.has(tag) }
  })
  const compiled = compileScript(descriptor, {
    id: `test-${page}`, inlineTemplate: true,
    templateOptions: { compilerOptions: { isCustomElement: tag => nativeTags.has(tag) } }
  })
  const context = vm.createContext({
    console,
    uni: {
      getStorageSync: key => storage.get(key), setStorageSync: (key, value) => storage.set(key, value),
      navigateTo: value => calls.push(value), switchTab: value => calls.push(value), redirectTo: value => calls.push(value)
    }
  })
  const module = new vm.SourceTextModule(compiled.content, { context })
  await module.link(name => {
    const values = name.endsWith('.vue')
      ? { default: name.endsWith('/MotionCollapse.vue') ? collapseComponent : genericComponent }
      : imports[name]
    assert.ok(values, `Unstubbed import: ${name}`)
    return new vm.SyntheticModule(Object.keys(values), function () {
      for (const [key, value] of Object.entries(values)) this.setExport(key, value)
    }, { context })
  })
  await module.evaluate()
  let render, tree
  const html = () => renderToString(Vue.createSSRApp({
    setup() {
      render ||= module.namespace.default.setup({}, { expose: value => Object.assign(exposed, value) })
      return () => { tree = render({}, []); return tree }
    }
  }))
  await html()
  return { state: exposed, calls, hooks, storage, render: () => tree, html }
}

function findNode(node, predicate) {
  if (!node || typeof node !== 'object') return null
  if (predicate(node)) return node
  const children = Array.isArray(node.children) ? node.children : node.children?.default?.() || []
  for (const child of children) {
    const match = findNode(child, predicate)
    if (match) return match
  }
  return null
}

test('guest home offers browsing/trial without personal empty sections or five expanded Jiangsu cards', async () => {
  const page = await pageFixture('home')
  const html = await page.html()
  assert.match(html, /今天，开口练一练/)
  assert.match(html, /登录后试用/)
  assert.match(html, /浏览题库/)
  assert.match(html, /题型训练/)
  assert.match(html, /定向备面/)
  assert.doesNotMatch(html, /home-section-(recent|ability|trend|weakness|recommendation)/)
  assert.doesNotMatch(html, /综合管理岗/)
  const toggle = findNode(page.render({}, []), node => node.props?.class === 'home-section-jiangsu')
  assert.ok(toggle, 'Jiangsu uses an independent MotionCollapse')
  toggle.props.onToggle()
  assert.match(await page.html(), /综合管理岗/)
})

test('returning learners see recent review before training routes and Jiangsu', async () => {
  const page = await pageFixture('home', { loggedIn: true, records: [{ examId: 'recent', questionSummary: '最近一次练习', totalScore: 80 }] })
  const html = await page.html()
  assert.ok(html.indexOf('最近一次练习') < html.indexOf('题型训练'))
  assert.ok(html.indexOf('最近一次练习') < html.indexOf('jiangsu-entry'))
  assert.match(html, /查看复盘/)
})

test('full-exam and pricing shortcuts precede recent practice and browsing sections for every login state', async () => {
  for (const loggedIn of [false, true]) {
    const page = await pageFixture('home', { loggedIn, records: loggedIn ? [{ examId: 'recent', questionSummary: '最近一次练习', totalScore: 80 }] : [] })
    const html = await page.html()
    const shortcuts = html.indexOf('class="quick-grid"')
    assert.ok(shortcuts > html.indexOf('learner-home__start'))
    assert.ok(shortcuts < html.indexOf(loggedIn ? 'home-section-recent' : 'guest-tip'), 'Main shortcuts must stay above variable personal/browsing content')
    assert.ok(shortcuts < html.indexOf('practice-routes'))
    assert.equal((html.match(/>全真练习<\/button>/g) || []).length, 1)
    assert.equal((html.match(/>套餐中心<\/button>/g) || []).length, 1)
  }
})

test('home keeps multi-open persisted sections, the native scroll hook and default practice routing', async () => {
  const page = await pageFixture('home', { loggedIn: true, storedSections: { trend: false } })
  assert.equal(page.state.sectionOpen.value.trend, false)
  page.state.toggleSection('trend')
  page.state.toggleSection('weakness')
  assert.equal(page.state.sectionOpen.value.recent, true)
  assert.equal(page.state.sectionOpen.value.trend, true)
  assert.equal(page.state.sectionOpen.value.weakness, false)
  assert.equal(JSON.parse(page.storage.get('civil_home_section_state')).trend, true)
  assert.equal(typeof page.hooks.onPageScroll, 'function')
  await page.state.goPractice('free')
  assert.equal(page.calls.at(-1).url, '/pages/exam/prepare?mode=free&trial=1')
  assert.doesNotMatch(page.calls.at(-1).url, /count|questionCount/)
})

test('fresh logged-in home has one useful empty state, not empty charts and recommendations', async () => {
  const page = await pageFixture('home', { loggedIn: true })
  const html = await page.html()
  assert.match(html, /home-section-recent/)
  assert.doesNotMatch(html, /home-section-(trend|weakness|recommendation)/)
})

test('login starts with WeChat primary, collapsed PC credentials and optional invite', async () => {
  const page = await pageFixture('login')
  const html = await page.html()
  assert.match(html, /class="primary-button wechat-login-button"/)
  assert.match(html, /已有 PC 账号/)
  assert.doesNotMatch(html, /请输入用户名|请输入密码|请输入邀请码/)
  assert.match(html, /先浏览/)
  const pcSection = findNode(page.render({}, []), node => node.props?.class === 'password-login-section')
  pcSection.props.onToggle()
  assert.match(await page.html(), /请输入用户名/)
  page.state.mode.value = 'register'
  assert.match(await page.html(), /请再次输入密码/)
})

test('WeChat privacy acknowledgement never silently checks the agreement or bypasses it', async () => {
  const page = await pageFixture('login')
  assert.equal(page.state.form.agreedTerms, false)
  page.state.onAgreePrivacyAuthorization()
  assert.equal(page.state.form.agreedTerms, false)
  await page.state.loginByWechat()
  assert.ok(!page.calls.includes('wechat'))
  page.state.toggleAgreement()
  await page.state.loginByWechat()
  assert.ok(page.calls.includes('wechat'))
})

test('optional invite stays available to both login modes and retains its value after collapse', async () => {
  const page = await pageFixture('login')
  const toggle = () => findNode(page.render(), node => node.props?.class === 'link-button invite-toggle')
  toggle().props.onTap()
  assert.match(await page.html(), /请输入邀请码/)
  page.state.form.inviteCode = 'INVITE_TEST'
  toggle().props.onTap()
  assert.doesNotMatch(await page.html(), /请输入邀请码/)
  assert.match(await page.html(), /已填写邀请码/)
  page.state.mode.value = 'register'
  assert.equal(page.state.form.inviteCode, 'INVITE_TEST')
  assert.equal(page.state.form.agreedTerms, false)
})

test('guest practice and browsing preserve login boundaries', async () => {
  const page = await pageFixture('home')
  await page.state.goPractice('free')
  assert.equal(page.calls.length, 1)
  assert.equal(page.calls[0].action, '专项练习')
  assert.equal(page.calls[0].url, '/pages/exam/prepare?mode=free')
  const bank = findNode(page.render(), node => node.type === 'navigator' && node.props?.url === '/pages/bank/index')
  assert.equal(bank.props['open-type'], 'switchTab')
})

test('existing PC account link opens password login when leaving account completion', async () => {
  const page = await pageFixture('login')
  page.state.accountSetupVisible.value = true
  await page.html()
  const button = findNode(page.render({}, []), node => node.type === 'button' && String(node.children).includes('已有电脑账号'))
  assert.ok(button)
  button.props.onTap()
  assert.equal(page.state.accountSetupVisible.value, false)
  assert.match(await page.html(), /请输入用户名/)
})

test('both pages compile scoped CSS and use shared UI token fallbacks', () => {
  for (const page of ['home', 'login']) {
    const { descriptor, errors } = parse(sourceOf(page))
    assert.deepEqual(errors, [])
    for (const style of descriptor.styles) {
      const compiled = compileStyle({ source: style.content, filename: `${page}.vue`, id: `test-${page}`, scoped: true })
      assert.deepEqual(compiled.errors, [])
    }
    assert.match(sourceOf(page), /var\(--ui-muted, #596a80\)/)
    assert.match(sourceOf(page), /min-height: 44px/)
    assert.doesNotMatch(sourceOf(page), /\binset\s*:/)
  }
})

test('both page templates compile to native WeChat WXML without writing shared build output', () => {
  for (const page of ['home', 'login']) {
    const { descriptor } = parse(sourceOf(page))
    const emitted = []
    const result = compileMiniTemplate(descriptor.template.content, {
      filename: `src/pages/${page}/index.vue`,
      miniProgram: {
        class: { array: true }, slot: { fallbackContent: false, dynamicSlotNames: true },
        event: { key: true }, directive: 'wx:', emitFile: asset => emitted.push(asset)
      }
    })
    assert.ok(result.code.length > 0)
    assert.equal(emitted.length, 1)
    assert.match(emitted[0].source, /<view/)
    assert.match(emitted[0].source, /wx:if/)
  }
})
