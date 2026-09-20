import test from 'node:test'
import assert from 'node:assert/strict'
import { existsSync, readFileSync } from 'node:fs'
import vm from 'node:vm'
import { TRAINING_CATEGORIES } from '../src/utils/constants.js'

const source = readFileSync(new URL('../src/pages/training/index.vue', import.meta.url), 'utf8')
const script = source.match(/<script setup>([^]*?)<\/script>/)[1].replace(/^import .*$/gm, '')
const template = source.match(/<template>([^]*?)<\/template>/)[1]
const style = source.match(/<style scoped>([^]*?)<\/style>/)[1]

function page(progress = {}) {
  const navigations = []
  const bindings = vm.runInNewContext(`${script}\n;({
    icons: typeof TRAINING_ICONS === 'undefined' ? null : TRAINING_ICONS,
    progressText, openDimension
  })`, {
    TRAINING_CATEGORIES,
    usePageMotion: () => ({ motionClass: [], motionStyle: {}, visible: { value: true } }),
    useTrainingStore: () => ({ getDimensionProgress: key => progress[key] || { attempts: 0 } }),
    uni: { navigateTo: value => navigations.push(value.url) }
  })
  return { ...bindings, navigations }
}

test('each training category uses a bundled Ant Design icon without changing shared category data', () => {
  const before = JSON.stringify(TRAINING_CATEGORIES)
  const { icons } = page()
  assert.ok(icons, 'the page must map category keys to existing local icon names')
  for (const category of TRAINING_CATEGORIES) {
    assert.ok(icons[category.key], `missing icon for ${category.key}`)
    assert.ok(existsSync(new URL(`../src/static/learner-icons/${icons[category.key]}.svg`, import.meta.url)))
  }
  assert.equal(JSON.stringify(TRAINING_CATEGORIES), before)
  assert.match(template, /<LearnerIcon\s+:name="TRAINING_ICONS\[category.key\]/)
  assert.doesNotMatch(template, /category\.(?:icon|tone)/)
})

test('training entry is a labelled native button with a 44px minimum hit area and visible focus', () => {
  assert.match(template, /<button\s+[^>]*v-for="category in TRAINING_CATEGORIES"[^>]*@tap="openDimension\(category\)"/)
  assert.match(template, /:aria-label="[^"\n]*category.name/)
  assert.match(style, /\.training-card\s*\{[^}]*min-height:\s*44px/)
  assert.match(style, /\.training-card:focus-visible\s*\{[^}]*outline:/)
})

test('training helper copy uses semantic colors and never shrinks below 14 logical pixels', () => {
  for (const selector of ['motion-eyebrow', 'page-desc', 'training-card__desc', 'training-card__meta']) {
    assert.match(style, new RegExp(`\\.${selector}\\s*\\{[^}]*font-size:\\s*(?:14px|max\\(14px,)`))
  }
  assert.match(style, /var\(--ui-muted(?:,|\))/)
  assert.match(style, /var\(--ui-link(?:,|\))/)
})

test('the existing accent follows page visibility rather than looping on hidden pages', () => {
  assert.match(script, /\{[^}]*visible[^}]*\}\s*=\s*usePageMotion\(\)/)
  assert.match(template, /<MotionAccent\s+:active="visible"/)
})

test('training progress retains the existing attempts and best-score contract', () => {
  const { progressText } = page({ analysis: { attempts: 3, bestScore: 82 } })
  assert.equal(progressText('analysis'), '练习 3 次 · 最佳 82 分')
  assert.equal(progressText('career'), '尚未练习')
})

test('training navigation retains the exact dimension route and encoded key', () => {
  const { openDimension, navigations } = page()
  for (const category of TRAINING_CATEGORIES) openDimension(category)
  openDimension({ key: 'a&b' })
  assert.deepEqual(navigations, [
    ...TRAINING_CATEGORIES.map(category => `/pages/training/dimension?key=${encodeURIComponent(category.key)}`),
    '/pages/training/dimension?key=a%26b'
  ])
})
