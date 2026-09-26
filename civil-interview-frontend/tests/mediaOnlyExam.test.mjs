import test from 'node:test'
import assert from 'node:assert/strict'
import { readFile } from 'node:fs/promises'
import vm from 'node:vm'

function loadFunction(source, name, context) {
  const declaration = source.match(new RegExp(`(?:async )?function ${name}\\([^]*?^}`, 'm'))?.[0]
  assert.ok(declaration, `${name} exists`)
  return vm.runInNewContext(`(${declaration})`, context)
}

test('history replay keeps all five questions and two unanswered placeholders after early exit', async () => {
  const source = await readFile(new URL('../src/views/Result/ResultPage.vue', import.meta.url), 'utf8')
  const ids = ['q3', 'q1', 'q5', 'q2', 'q4']
  const answered = ids.slice(0, 3).map(questionId => ({ questionId, transcript: '真实作答', scoringResult: { totalScore: 70 } }))
  const rows = loadFunction(source, 'buildDisplayAnswerList', {})(answered, ids, 'exam')
  assert.deepEqual(Array.from(rows, row => row.questionId), ids)
  assert.equal(rows.filter(row => row.isPlaceholder).length, 2)
  assert.equal(rows[2].scoringResult.totalScore, 70)
})

test('full exam records and submits media even with a legacy text-mode state', async () => {
  const source = await readFile(new URL('../src/components/exam/FullExamRoom.vue', import.meta.url), 'utf8')
  const calls = []
  let started = 0
  let stopped = 0
  let blob = { size: 120 }
  const state = {
    status: 'idle', currentIndex: 0, answerMode: 'text', answers: [], totalQuestions: 3, examStartTime: Date.now(), goToQuestion() {},
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
    submittingAnswer: { value: false }, exitingExam: { value: false },
    totalRemainingSeconds: { value: 600 }, recorderDuration: { value: 0 },
    recorder: { startRecording: () => started++, stopRecording: async () => { stopped++; return blob } },
    syncUsage: async () => {}, message: { success() {}, error: text => assert.fail(text), warning: text => assert.fail(text) }
  }
  await loadFunction(source, 'startCurrentAnswer', context)()
  assert.equal(state.status, 'answering')
  assert.equal(started, 1)
  await loadFunction(source, 'submitCurrentAnswer', context)()
  await loadFunction(source, 'submitCurrentAnswerForExit', context)()
  assert.equal(calls.length, 2)
  assert.equal(stopped, 2)
  assert.ok(calls.every(call => call.blob === blob && call.transcript === undefined))
  blob = { size: 0 }
  assert.equal(await loadFunction(source, 'submitCurrentAnswerForExit', context)(), null)
})

test('standard practice records and preserves the current media on interrupted exit', async () => {
  const source = await readFile(new URL('../src/components/exam/StandardExamRoom.vue', import.meta.url), 'utf8')
  let started = 0
  let blob = { size: 120 }
  const calls = []
  const state = {
    answerMode: 'text', status: 'idle', currentQuestion: {}, isLastQuestion: true,
    startAnswering() { this.status = 'answering' },
    submitAnswer: async (...args) => { calls.push(args); return {} }
  }
  const context = {
    examStore: state, EXAM_STATUS: { ANSWERING: 'answering' },
    countdown: { stop() {}, reset() {}, onFinish() {}, start() {} },
    recorder: { startRecording: () => started++, stopRecording: async () => blob },
    recorderDuration: { value: 1 }, textAnswer: { value: '旧文字输入' },
    finishRequested: { value: false }, syncUsage: async () => {},
    submittingAnswer: { value: false }, exitingExam: { value: false }, onFinish: async () => {},
    message: { error: text => assert.fail(text) }
  }
  loadFunction(source, 'onStartAnswer', context)()
  assert.equal(started, 1)
  await loadFunction(source, 'onSubmit', context)()
  await loadFunction(source, 'submitCurrentAnswerForExit', context)()
  assert.deepEqual(calls, [[blob], [blob]])
  blob = null
  assert.equal(await loadFunction(source, 'submitCurrentAnswerForExit', context)(), null)
})

test('both clients expose media controls without a typed-answer entry', async () => {
  const files = [
    '../src/views/Exam/ExamPrepare.vue',
    '../src/components/exam/StandardExamRoom.vue',
    '../src/components/exam/FullExamRoom.vue',
    '../../civil-interview-miniprogram/src/pages/exam/prepare.vue',
    '../../civil-interview-miniprogram/src/pages/exam/room.vue'
  ]
  for (const file of files) {
    const source = await readFile(new URL(file, import.meta.url), 'utf8')
    assert.doesNotMatch(source, /文字作答|提交文字答案|<a-textarea|<textarea|textAnswer/, file)
    assert.match(source, /录音|录制/, `${file} retains media controls`)
  }
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
