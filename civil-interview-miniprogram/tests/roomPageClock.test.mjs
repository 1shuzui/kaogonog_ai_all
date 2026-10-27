import { useExamClock } from '../src/composables/useExamClock.mjs'
import { useFloatingCamera } from '../src/composables/useFloatingCamera.mjs'
import test from 'node:test'
import assert from 'node:assert/strict'
import vm from 'node:vm'
import { readFileSync } from 'node:fs'
import * as Vue from 'vue'
import { parse, compileScript } from '@vue/compiler-sfc'
const pageSource = readFileSync(new URL('../src/pages/exam/room.vue', import.meta.url), 'utf8')
const { descriptor } = parse(pageSource)
const imports = compileScript(descriptor, { id: 'question-binding' }).scriptSetupAst.filter(node => node.type === 'ImportDeclaration')
const script = [...imports].reverse().reduce((source, node) => source.slice(0,node.start)+source.slice(node.end), descriptor.scriptSetup.content)

test('real room respects an explicit zero-second preparation time', async t => {
  const scope = Vue.effectScope(); t.after(() => scope.stop())
  const store = Vue.reactive({ source: 'targeted', examId: 'e-zero', currentIndex: 0, loading: false, answers: [], mediaMode: 'audio',
    questions: [{ id: 'q-zero', stem: '零准备定向题', prepTime: 0, answerTime: 180 }],
    get currentQuestion() { return this.questions[this.currentIndex] }, get totalQuestions() { return 1 },
    get questionNumber() { return 1 }
  })
  const context = vm.createContext({ ...Vue, useExamClock, useFloatingCamera, console, setInterval, clearInterval, setTimeout, clearTimeout,
    onLoad() {}, onHide() {}, onReady() {}, onBeforeUnmount() {}, uni: { setNavigationBarTitle() {} },
    usePageMotion: () => ({ motionClass: '', motionStyle: {}, visible: Vue.ref(true), mode: Vue.ref('full') }),
    useExamStore: () => store, useSubscriptionStore: () => ({}),
    useUserStore: () => ({ preferences: { defaultPrepTime: 90, defaultAnswerTime: 180 } }),
    getProvinceName: value => value, getCategoryName: value => value, formatTime: String, toast() {}
  })
  const page = scope.run(() => vm.runInContext(`${script}\n;({resetQuestionState, prepLeft, standardQuestionSeconds})`, context))
  page.resetQuestionState()
  assert.equal(page.prepLeft.value, 0)
  assert.equal(page.standardQuestionSeconds(), 180)
})
