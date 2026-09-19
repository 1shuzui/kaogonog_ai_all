import test from 'node:test'
import assert from 'node:assert/strict'
import { readFile } from 'node:fs/promises'
import vm from 'node:vm'

function loadFunction(source, name, context) {
  const declaration = source.match(new RegExp(`(?:async )?function ${name}\\([^]*?^}`, 'm'))?.[0]
  assert.ok(declaration, `${name} exists`)
  return vm.runInNewContext(`(${declaration})`, context)
}

test('full exam text start, submit, and interrupted exit never require a recorder', async () => {
  const source = await readFile(new URL('../src/components/exam/FullExamRoom.vue', import.meta.url), 'utf8')
  const calls = []
  const state = {
    status: 'idle', currentIndex: 0,
    resetCurrentQuestionState() {},
    startAnswering() { this.status = 'answering' },
    async submitAnswer(blob, transcript) { calls.push({ blob, transcript }); return { examId: 'exam', questionId: 'q1' } }
  }
  const context = {
    examStore: state, examStarted: { value: true }, readingPhaseActive: { value: false },
    currentAnswer: { value: null }, nextPendingIndex: { value: 0 },
    isFutureQuestion: () => false, stopSpeech() {},
    isTextAnswer: { value: true }, textAnswer: { value: '先调查诉求，再协调处理并回访。' },
    EXAM_STATUS: { ANSWERING: 'answering' }, finishRequested: { value: false },
    totalRemainingSeconds: { value: 600 }, recorderDuration: { value: 0 },
    recorder: { startRecording: () => assert.fail('text must not start recorder'), stopRecording: () => assert.fail('text must not stop recorder') },
    syncUsage: async () => {}, message: { error: text => assert.fail(text), warning: text => assert.fail(text) }
  }
  await loadFunction(source, 'startCurrentAnswer', context)()
  assert.equal(state.status, 'answering')
  await loadFunction(source, 'submitCurrentAnswer', context)()
  await loadFunction(source, 'submitCurrentAnswerForExit', context)()
  assert.equal(calls.length, 2)
  assert.ok(calls.every(call => call.blob === null && call.transcript === context.textAnswer.value))
  context.textAnswer.value = '  '
  assert.equal(await loadFunction(source, 'submitCurrentAnswerForExit', context)(), null)
})

test('web multi-question training passes every selected question in order', async () => {
  const source = await readFile(new URL('../src/views/Training/DimensionTraining.vue', import.meta.url), 'utf8')
  let navigation
  const context = {
    questions: { value: [{ id: 'q1' }, { id: 'q2' }, { id: 'q3' }, { id: 'q4' }, { id: 'q5' }] },
    isQuestionScoringSupported: () => true,
    router: { push: route => { navigation = route } }
  }
  loadFunction(source, 'startAllQuestions', context)()
  assert.equal(navigation.query.source, 'training')
  assert.equal(navigation.query.questionIds, 'q1,q2,q3,q4,q5')
})
