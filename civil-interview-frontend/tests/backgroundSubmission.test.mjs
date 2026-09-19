import test from 'node:test'
import assert from 'node:assert/strict'
import { readFile } from 'node:fs/promises'
import vm from 'node:vm'

const STATUS = { IDLE: 'idle', PREPARING: 'preparing', ANSWERING: 'answering', SUBMITTING: 'submitting', COMPLETED: 'completed' }
const TRANSCRIPT = '第一题：先了解实际情况，再协调资源解决问题，最后回访。'
const SCORE = { totalScore: 78, maxScore: 100 }
const ref = value => ({ value })
// One event-loop turn drains ready promise jobs; no timeout, sleep or network.
const flush = () => new Promise(resolve => setImmediate(resolve))

function deferred() {
  let resolve, reject
  const promise = new Promise((yes, no) => { resolve = yes; reject = no })
  return { promise, resolve, reject }
}

function observe(promise) {
  const result = { done: false, error: null }
  result.promise = promise.then(() => { result.done = true }, error => { result.error = error })
  return result
}

function extractSFC(source, name, context) {
  const declaration = source.match(new RegExp(`(?:async )?function ${name}\\([^]*?^}`, 'm'))?.[0]
  assert.ok(declaration, `${name} exists in the actual component`)
  return vm.runInContext(`(${declaration})`, context)
}

async function createStore(api = {}, runtime = {}) {
  const source = await readFile(new URL('../src/stores/exam.js', import.meta.url), 'utf8')
  const context = vm.createContext({
    Blob, localStorage: { getItem: key => key === 'token' ? 'test-session-a' : null }, ...runtime
  })
  const module = new vm.SourceTextModule(source, { context })
  const mocks = {
    pinia: { defineStore: (_, options) => options },
    '@/utils/constants': { EXAM_STATUS: STATUS },
    '@/api/exam': {
      startExam: api.start || (async () => ({ examId: 'background-web' })), uploadRecording: api.upload || (async () => ({})),
      completeExam: api.complete || (async () => ({}))
    },
    '@/api/scoring': {
      transcribeAudio: api.transcribe || (async () => ({ transcript: TRANSCRIPT })),
      evaluateAnswer: api.evaluate || (async () => SCORE)
    },
    '@/utils/scoringSupport': {
      getScoringUnavailableMessage: () => '题目不可评分',
      isQuestionIdScoringSupported: () => true, normalizeScoringErrorMessage: text => text
    }
  }
  await module.link(name => {
    assert.ok(mocks[name], `explicit mock for ${name}`)
    return new vm.SyntheticModule(Object.keys(mocks[name]), function () {
      for (const [key, value] of Object.entries(mocks[name])) this.setExport(key, value)
    }, { context })
  })
  await module.evaluate()
  const options = module.namespace.useExamStore
  const store = Object.assign(options.state(), options.actions)
  store.$reset = () => Object.assign(store, options.state())
  for (const [key, getter] of Object.entries(options.getters)) Object.defineProperty(store, key, { get: () => getter(store) })
  await store.initExam(['q1', 'q2', 'q3'].map(id => ({ id, prepTime: 90, answerTime: 180 })))
  return store
}

async function createCountdown(seconds) {
  let now = 1000, nextTimerId = 0
  const timers = new Map(), unmount = []
  const context = vm.createContext({
    performance: { now: () => now },
    Date: class extends Date { static now() { return now } },
    setInterval: callback => { const id = ++nextTimerId; timers.set(id, callback); return id },
    clearInterval: id => timers.delete(id)
  })
  const source = await readFile(new URL('../src/composables/useCountdown.js', import.meta.url), 'utf8')
  const module = new vm.SourceTextModule(source, { context })
  const mocks = {
    vue: { ref, computed: getter => ({ get value() { return getter() } }), onUnmounted: callback => unmount.push(callback) },
    '@/utils/formatter': { formatTime: value => String(value) }
  }
  await module.link(name => {
    assert.ok(mocks[name], `explicit mock for ${name}`)
    return new vm.SyntheticModule(Object.keys(mocks[name]), function () {
      for (const [key, value] of Object.entries(mocks[name])) this.setExport(key, value)
    }, { context })
  })
  await module.evaluate()
  return {
    countdown: module.namespace.useCountdown(seconds), timers,
    at(milliseconds, deliverTick = true) {
      assert.ok(milliseconds >= now, 'the fake monotonic clock cannot run backwards')
      now = milliseconds
      if (deliverTick) for (const callback of [...timers.values()]) callback()
    },
    dispose() { for (const callback of unmount) callback() }
  }
}

test('Standard onSubmit advances while upload and usage are pending, with duration fixed at the click', async () => {
  const upload = deferred(), usage = deferred(), stopped = deferred()
  const store = await createStore({ upload: () => upload.promise })
  store.startAnswering()
  const blob = new Blob(['question-one'], { type: 'audio/webm' })
  const duration = ref(23.2), errors = [], usageCalls = []
  let countdownRunning = true
  const source = await readFile(new URL('../src/components/exam/StandardExamRoom.vue', import.meta.url), 'utf8')
  const context = vm.createContext({
    examStore: store, EXAM_STATUS: STATUS, finishRequested: ref(false), recorderDuration: duration,
    submittingAnswer: ref(false), exitingExam: ref(false),
    recorder: { stopRecording: () => stopped.promise },
    countdown: { stop: () => { countdownRunning = false }, reset() {} },
    syncUsage: (answer, seconds) => { usageCalls.push({ questionId: answer.questionId, seconds }); return usage.promise },
    message: { success() {}, error: text => errors.push(text) }
  })
  context.onNext = extractSFC(source, 'onNext', context)
  const pending = observe(extractSFC(source, 'onSubmit', context)())
  // A slow recorder flush must not add 60 seconds to this question's usage.
  duration.value += 60
  stopped.resolve(blob)
  try {
    await flush()
    assert.equal(pending.error, null)
    assert.deepEqual(errors, [])
    assert.deepEqual(usageCalls, [{ questionId: 'q1', seconds: 24 }])
    assert.equal(countdownRunning, false)
    assert.equal(store.answers[0].recordingBlob, blob)
    assert.deepEqual({ questionIndex: store.currentIndex, returned: pending.done },
      { questionIndex: 1, returned: true }, 'neither upload nor usage may hold the next question')
  } finally {
    stopped.resolve(blob)
    usage.resolve({})
    upload.resolve({})
    await pending.promise
    await store.waitForPendingProcessing()
  }
})

test('Full submit advances to the next unanswered question before usage resolves without restarting Jiangsu 5+15', async () => {
  const upload = deferred(), usage = deferred(), stopped = deferred()
  const store = await createStore({ upload: () => upload.promise })
  store.fullExamMode = true
  store.examStartTime = 10000
  store.examElapsed = 421
  store.answers.push({ examId: store.examId, questionId: 'q1', questionIndex: 0, processingStatus: 'completed' })
  store.goToQuestion(1)
  store.startAnswering()
  const source = await readFile(new URL('../src/components/exam/FullExamRoom.vue', import.meta.url), 'utf8')
  const errors = [], usageCalls = [], duration = ref(18.1), totalRemaining = ref(779)
  const context = vm.createContext({
    examStore: store, EXAM_STATUS: STATUS, finishRequested: ref(false), recorderDuration: duration,
    submittingAnswer: ref(false), exitingExam: ref(false),
    Date: class extends Date { static now() { return 431000 } },
    examStarted: ref(true), readingPhaseActive: ref(false), isJiangsuFullExamTiming: ref(true),
    totalRemainingSeconds: totalRemaining, totalDurationSeconds: ref(300 + 900),
    currentAnswer: { get value() { return store.currentAnswer } },
    nextPendingIndex: { get value() { return store.answers.length } },
    allAnswered: { get value() { return store.answers.length === store.totalQuestions } },
    canGoNext: { get value() { return !store.isLastQuestion } },
    recorder: { stopRecording: () => stopped.promise, startRecording() {} },
    syncUsage: (answer, seconds) => { usageCalls.push({ questionId: answer.questionId, seconds }); return usage.promise },
    stopSpeech() {}, finishExam: async () => { throw new Error('not the final question') },
    message: { info() {}, success() {}, warning: text => errors.push(text), error: text => errors.push(text) }
  })
  for (const name of ['returnToPendingQuestion', 'goNextQuestion', 'selectQuestion', 'isFutureQuestion', 'startCurrentAnswer']) {
    context[name] = extractSFC(source, name, context)
  }
  const pending = observe(extractSFC(source, 'submitCurrentAnswer', context)())
  duration.value += 60
  stopped.resolve(new Blob(['question-two']))
  try {
    await flush()
    assert.equal(pending.error, null)
    assert.deepEqual(errors, [])
    assert.deepEqual(usageCalls, [{ questionId: 'q2', seconds: 19 }])
    assert.deepEqual({ start: store.examStartTime, elapsed: store.examElapsed, remaining: totalRemaining.value, reading: context.readingPhaseActive.value },
      { start: 10000, elapsed: 421, remaining: 779, reading: false }, 'advancing must retain the same 300+900 second exam budget')
    assert.deepEqual({ questionIndex: store.currentIndex, returned: pending.done },
      { questionIndex: 2, returned: true }, 'submission must automatically advance to q3 while q2 processes')
  } finally {
    usage.resolve({})
    upload.resolve({})
    await pending.promise
    await store.waitForPendingProcessing()
  }
})

test('web duplicate submissions share one saved answer; delayed failure and retry cannot overwrite the next question', async () => {
  const upload = deferred(), asr = deferred(), scoring = deferred()
  let uploads = 0, transcriptions = 0, retry = false
  const store = await createStore({
    upload: () => { uploads++; return upload.promise },
    transcribe: () => { transcriptions++; return asr.promise },
    evaluate: () => retry ? Promise.resolve(SCORE) : scoring.promise
  })
  const blob = new Blob(['first recording']), nextBlob = new Blob(['next recording'])
  await store.submitAnswer(blob)
  await store.submitAnswer(blob)
  const queued = store.answers.find(answer => answer.questionId === 'q1')
  const savedCount = store.answers.length
  store.nextQuestion()
  store.startAnswering()
  store.recordingBlob = nextBlob
  store.transcript = '第二题正在作答'
  store.scoringResult = null
  upload.resolve({})
  asr.resolve({ transcript: TRANSCRIPT })
  await flush()
  scoring.reject(new Error('mock scoring timeout'))
  await store.waitForPendingProcessing()
  const failureRetained = queued.processingStatus === 'failed' && queued.transcript === TRANSCRIPT && queued.recordingBlob === blob
  retry = true
  await store.queueExamAnswerProcessing(queued)
  assert.deepEqual({ index: store.currentIndex, status: store.status, transcript: store.transcript, result: store.scoringResult },
    { index: 1, status: 'answering', transcript: '第二题正在作答', result: null })
  assert.equal(store.recordingBlob, nextBlob, 'a late q1 completion must not replace q2 recording')
  assert.deepEqual({ savedCount, uploads, transcriptions, failureRetained, retried: queued.processingStatus },
    { savedCount: 1, uploads: 1, transcriptions: 1, failureRetained: true, retried: 'completed' },
    'the same exam/question must be idempotent and retain media/transcript for a scoring-only retry')
})

test('web finish closes immediately, then refreshes the captured exam only after its queued scoring finishes', async () => {
  const scoring = deferred(), close = deferred(), calls = []
  let graded = false
  const store = await createStore({
    evaluate: () => scoring.promise,
    complete: examId => { calls.push({ examId, graded }); return close.promise }
  })
  assert.equal(typeof store.finish, 'function', 'PC store needs a finish() lifecycle independent of the room')
  const answer = await store.submitAnswer(new Blob(['recording']))
  await flush()
  const originalExamId = store.examId
  const pending = observe(Promise.resolve(store.finish()))
  const immediately = calls.map(call => ({ ...call }))
  try {
    close.resolve({})
    await flush()
    const beforeScoring = calls.length
    // A subsequent exam must not become the target of the previous exam's refresh.
    store.examId = 'subsequent-web-exam'
    graded = true
    scoring.resolve(SCORE)
    await store.waitForPendingProcessing()
    await pending.promise
    await flush()
    assert.equal(pending.error, null)
    assert.deepEqual({ immediately, beforeScoring, afterScoring: calls }, {
      immediately: [{ examId: originalExamId, graded: false }], beforeScoring: 1,
      afterScoring: [{ examId: originalExamId, graded: false }, { examId: originalExamId, graded: true }]
    }, 'close time is recorded before grading; the later refresh must not use mutable this.examId')
    assert.equal(store.examId, 'subsequent-web-exam')
    assert.ok(store.answers.includes(answer), 'finish must not discard an answer still owned by its processing task')
    assert.equal(answer.scoringResult.totalScore, 78)
  } finally {
    close.resolve({})
    scoring.resolve(SCORE)
    await pending.promise
  }
})

test('both PC rooms open the result page without awaiting finalization or clearing the queued answers', async () => {
  const outcomes = []
  for (const [component, handler] of [['StandardExamRoom', 'onFinish'], ['FullExamRoom', 'finishExam']]) {
    const queue = deferred(), navigation = [], errors = []
    let finalizations = 0
    const answer = { questionId: 'q1', processingStatus: 'scoring' }
    const store = {
      examId: 'web-finishing', answers: [answer],
      finish: () => { finalizations++; return queue.promise },
      evaluatePendingAnswers: () => queue.promise,
      exitExam() { this.answers = []; this.examId = null }
    }
    const source = await readFile(new URL(`../src/components/exam/${component}.vue`, import.meta.url), 'utf8')
    const context = vm.createContext({
      examStore: store, finishRequested: ref(false),
      stopTotalTimer() {}, stopSpeech() {}, countdown: { stop() {} }, recorder: { destroyStream() {} },
      completeExam: async () => ({}), router: { push: path => navigation.push(path) },
      message: { error: text => errors.push(text) }, logger: { error: text => errors.push(text) }
    })
    const pending = observe(extractSFC(source, handler, context)())
    await flush()
    const beforeQueue = { component, navigation: [...navigation], finalizations, returned: pending.done }
    queue.resolve({})
    await pending.promise
    assert.equal(pending.error, null)
    assert.deepEqual(errors, [])
    outcomes.push({ ...beforeQueue, retainedAnswer: store.answers.includes(answer) })
  }
  assert.deepEqual(outcomes, ['StandardExamRoom', 'FullExamRoom'].map(component => ({
    component, navigation: ['/result/web-finishing'], finalizations: 1, returned: true, retainedAnswer: true
  })), 'navigating away is independent of background grading and must preserve its source data')
})

test('useCountdown catches up delayed ticks without dropping fractional elapsed seconds', async () => {
  const clock = await createCountdown(5), samples = []
  let finished = 0
  clock.countdown.onFinish(() => { finished++ })
  try {
    clock.countdown.start()
    for (const time of [2500, 4000, 6000]) {
      clock.at(time)
      samples.push(clock.countdown.remaining.value)
    }
    clock.at(16000)
    assert.deepEqual({ samples, finished, running: clock.countdown.isRunning.value, timers: clock.timers.size },
      { samples: [4, 2, 0], finished: 1, running: false, timers: 0 }, '1.5s + 1.5s + 2s must consume exactly 5 seconds')
  } finally {
    clock.dispose()
  }
})

test('useCountdown pause/resume retains sub-second work and excludes all paused time', async () => {
  const clock = await createCountdown(3), samples = []
  let finished = 0
  clock.countdown.onFinish(() => { finished++ })
  try {
    clock.countdown.start()
    clock.at(1450, false) // 450ms of active time, before any delivered tick.
    clock.countdown.pause()
    const pausedRemaining = clock.countdown.remaining.value
    clock.at(6450) // Five seconds paused must not consume any answer time.
    assert.equal(clock.countdown.remaining.value, pausedRemaining)
    clock.countdown.start()
    clock.at(7000) // 450 + 550 = 1000ms of active time.
    samples.push(clock.countdown.remaining.value)
    clock.at(7250, false)
    clock.countdown.pause()
    clock.at(9250)
    clock.countdown.start()
    clock.at(10000) // 1000 + 250 + 750 = 2000ms active.
    samples.push(clock.countdown.remaining.value)
    clock.at(11000) // 3000ms active in total.
    samples.push(clock.countdown.remaining.value)
    assert.deepEqual({ samples, finished, timers: clock.timers.size }, { samples: [2, 1, 0], finished: 1, timers: 0 },
      'sub-second recording time must survive both pauses instead of extending the exam')
  } finally {
    clock.dispose()
  }
})

test('web account changes between upload/ASR stages prevent every subsequent request under the new token', async () => {
  const outcomes = []
  for (const switchAfter of ['upload', 'asr']) {
    const upload = deferred(), asr = deferred(), calls = []
    const storage = new Map([['token', 'test-account-a']])
    const record = stage => calls.push({ stage, token: storage.get('token') })
    const store = await createStore({
      upload: () => { record('upload'); return upload.promise },
      transcribe: () => { record('asr'); return asr.promise },
      evaluate: async () => { record('score'); return SCORE }
    }, { localStorage: { getItem: key => storage.get(key) || null } })
    await store.submitAnswer(new Blob(['account-a recording']))
    await flush()
    if (switchAfter === 'asr') {
      upload.resolve({})
      await flush()
    }
    storage.set('token', 'test-account-b')
    upload.resolve({})
    asr.resolve({ transcript: TRANSCRIPT })
    await store.waitForPendingProcessing()
    outcomes.push({ switchAfter, calls })
  }
  assert.deepEqual(outcomes, [
    { switchAfter: 'upload', calls: [{ stage: 'upload', token: 'test-account-a' }] },
    { switchAfter: 'asr', calls: [{ stage: 'upload', token: 'test-account-a' }, { stage: 'asr', token: 'test-account-a' }] }
  ], 'API responses are deliberately allowed to resolve; the store must check its captured session before the next stage')
})

test('web keeps the previous exam task and failed recording reachable across a successful new start', async () => {
  const upload = deferred(), starting = deferred()
  let starts = 0, uploads = 0, evaluations = 0
  const store = await createStore({
    start: () => ++starts === 2 ? starting.promise : Promise.resolve({ examId: `web-${starts}` }),
    upload: () => { uploads++; return upload.promise },
    evaluate: async () => { if (++evaluations === 1) throw new Error('model offline'); return SCORE }
  })
  const blob = new Blob(['previous exam recording'])
  const old = await store.submitAnswer(blob), oldId = store.examId
  const beginning = observe(store.initExam([{ id: 'new-question' }]))
  try {
    assert.equal(store.answers[0], old, 'starting the server session must not clear the current answer early')
    starting.resolve({ examId: 'web-2' })
    await beginning.promise
    assert.equal(beginning.error, null)
    assert.equal(store.answers.length, 0)
    assert.equal(store.getAnswersForExam(oldId)[0], old)
    assert.equal(store.pendingAnswers[0], old)
    const waiting = observe(store.waitForPendingProcessing(oldId))
    await flush()
    assert.equal(waiting.done, false, 'new exams must not clear a previous exam processing map')
    store.startAnswering()
    store.transcript = '新场当前作答'
    upload.resolve({})
    await waiting.promise
    assert.equal(old.processingStatus, 'failed')
    assert.equal(old.recordingBlob, blob)
    assert.equal(old.transcript, TRANSCRIPT)
    assert.equal(store.pendingAnswers[0], old)
    assert.equal(await store.retryAnswer({ ...old }), null, 'a copied or forged answer is not an owned task')
    const retry = store.retryAnswer(old)
    await Promise.all([retry, store.retryAnswer(old)])
    assert.equal(old.processingStatus, 'completed')
    assert.equal(store.getAnswersForExam(oldId)[0], old, 'recently completed archive results remain readable')
    assert.equal(store.pendingAnswers.length, 0)
    assert.equal(store.getAnswersForExam('unknown').length, 0)
    assert.equal(store.transcript, '新场当前作答')
    assert.equal(store.scoringResult, null)
    assert.deepEqual({ uploads, evaluations }, { uploads: 1, evaluations: 2 })
    await store.initExam([{ id: 'third-question' }])
    assert.equal(store.getAnswersForExam(oldId)[0], old, 'a subsequent start must not erase a completed archive from an open result page')
    assert.equal(store.pendingAnswers.length, 0, 'completed archives are retained results, not pending task reminders')
  } finally {
    starting.resolve({ examId: 'web-2' })
    upload.resolve({})
    await beginning.promise
    await store.waitForPendingProcessing(oldId)
  }
})

test('web archived result views retain already-completed and late-completed answers until session reset', async () => {
  const scoring = deferred()
  let starts = 0
  const store = await createStore({
    start: async () => ({ examId: `retained-web-${++starts}` }),
    evaluate: ({ questionId }) => questionId === 'q2' ? scoring.promise : Promise.resolve(SCORE)
  })
  const oldId = store.examId
  const first = await store.submitAnswer(new Blob(['first recording']))
  await store.waitForPendingProcessing(oldId)
  assert.equal(first.processingStatus, 'completed')
  store.goToQuestion(1)
  const second = await store.submitAnswer(new Blob(['second recording']))
  try {
    await store.initExam([{ id: 'next-exam-question' }])
    const before = store.getAnswersForExam(oldId)
    assert.equal(before.length, 2, 'the old result view must retain answers already completed before archiving too')
    assert.equal(before[0], first)
    assert.equal(before[1], second)
    assert.equal(store.pendingAnswers.length, 1)
    assert.equal(store.pendingAnswers[0], second)
    scoring.resolve({ totalScore: 86, maxScore: 100 })
    await store.waitForPendingProcessing(oldId)
    assert.equal(store.pendingAnswers.length, 0)
    assert.equal(store.getAnswersForExam(oldId)[1], second)
    assert.equal(second.scoringResult.totalScore, 86)
    await store.initExam([{ id: 'another-exam-question' }])
    const after = store.getAnswersForExam(oldId)
    assert.equal(after.length, 2, 'a later start cannot empty the watched exam result set or duplicate its answers')
    assert.equal(after[0], first)
    assert.equal(after[1], second)
    assert.equal(after[0].scoringResult.totalScore, 78)
    assert.equal(after[1].scoringResult.totalScore, 86)
    store.$reset()
    assert.equal(store.getAnswersForExam(oldId).length, 0)
    assert.equal(store.pendingAnswers.length, 0)
    assert.equal(await store.retryAnswer(first), null, 'reset also releases ownership of completed archived answers')
  } finally {
    scoring.resolve(SCORE)
    await store.waitForPendingProcessing(oldId)
  }
})

test('web resolved scoring responses need a finite score; invalid responses retain retryable media/transcript and genuine zero succeeds', async () => {
  const invalidResults = [undefined, null, {}, { totalScore: null }, { totalScore: '' }, { totalScore: ' ' },
    { totalScore: NaN }, { totalScore: Infinity }, { totalScore: 'not-a-score' }, { score: -Infinity },
    { totalScore: false }, { score: [] }]
  for (const [index, invalidResult] of invalidResults.entries()) {
    const scoring = deferred()
    let uploads = 0, transcriptions = 0, evaluations = 0
    const store = await createStore({
      upload: async () => { uploads++; return {} },
      transcribe: async () => { transcriptions++; return { transcript: TRANSCRIPT } },
      evaluate: async payload => {
        assert.equal(payload.transcript, TRANSCRIPT)
        return ++evaluations === 1 ? scoring.promise : index % 2 ? { score: 0 } : { totalScore: 0 }
      }
    })
    const blob = new Blob(['retained despite HTTP 200']), answer = await store.submitAnswer(blob)
    scoring.resolve(invalidResult) // A fulfilled HTTP response, not a rejected network request.
    await store.waitForPendingProcessing()
    assert.equal(answer.processingStatus, 'failed', `invalid successful response ${index} must remain retryable`)
    assert.equal(answer.transcript, TRANSCRIPT)
    assert.equal(answer.recordingBlob, blob)
    assert.equal(answer.scoringResult, null)
    assert.equal(store.scoringResult, null)
    assert.ok(answer.processingError)
    assert.equal(store.pendingAnswers[0], answer)
    assert.equal(await store.retryAnswer(answer), answer)
    assert.equal(answer.processingStatus, 'completed', 'numeric zero is a real score, not a missing result')
    assert.equal(answer.scoringResult.totalScore ?? answer.scoringResult.score, 0)
    assert.equal(answer.transcript, TRANSCRIPT)
    assert.equal(store.pendingAnswers.length, 0)
    assert.deepEqual({ uploads, transcriptions, evaluations }, { uploads: 1, transcriptions: 1, evaluations: 2 })
  }
})

test('web archives all three answers of a partly failed exam and releases media only after the whole exam completes', async () => {
  const retryScoring = deferred(), blobs = [], original = []
  let starts = 0, thirdAttempts = 0, rejectStart = false
  const store = await createStore({
    start: async () => {
      if (rejectStart) throw new Error('start unavailable')
      return { examId: `three-web-${++starts}` }
    },
    evaluate: async ({ questionId }) => {
      if (questionId === 'other-failed' || (questionId === 'q3' && ++thirdAttempts === 1)) throw new Error('model offline')
      return questionId === 'q3' ? retryScoring.promise : SCORE
    }
  })
  const oldId = store.examId
  for (let index = 0; index < 3; index++) {
    store.goToQuestion(index)
    blobs.push(new Blob([`recording-${index}`]))
    original.push(await store.submitAnswer(blobs[index]))
    await store.waitForPendingProcessing(oldId)
  }
  assert.deepEqual(original.map(answer => answer.processingStatus), ['completed', 'completed', 'failed'])
  try {
    await store.initExam([{ id: 'other-failed' }])
    const archived = store.getAnswersForExam(oldId)
    assert.equal(archived.length, 3, 'two completed answers must accompany the failed answer into the archive')
    for (let index = 0; index < 3; index++) {
      assert.equal(archived[index], original[index])
      assert.equal(archived[index].recordingBlob, blobs[index], 'retain the entire exam media while any answer is unfinished')
    }
    assert.equal(archived[0].scoringResult.totalScore, 78)
    assert.equal(archived[1].scoringResult.totalScore, 78)
    assert.equal(store.pendingAnswers.length, 1)
    assert.equal(store.pendingAnswers[0], original[2])
    const otherBlob = new Blob(['another exam recording'])
    const other = await store.submitAnswer(otherBlob)
    await store.waitForPendingProcessing()
    const retry = store.retryAnswer(original[2])
    await flush()
    await store.initExam([{ id: 'new-question' }])
    for (let index = 0; index < 3; index++) assert.equal(original[index].recordingBlob, blobs[index])
    retryScoring.resolve({ totalScore: 86, maxScore: 100 })
    await retry
    assert.equal(store.pendingAnswers.length, 1)
    assert.equal(store.pendingAnswers[0], other)
    for (let index = 0; index < 3; index++) assert.equal(original[index].recordingBlob, blobs[index], 'completion itself must not dispose media')
    rejectStart = true
    await assert.rejects(store.initExam([{ id: 'rejected-question' }]), /start unavailable/)
    for (let index = 0; index < 3; index++) assert.equal(original[index].recordingBlob, blobs[index], 'failed starts cannot collect archived media')
    rejectStart = false
    await store.initExam([{ id: 'next-question' }])
    const retained = store.getAnswersForExam(oldId)
    assert.equal(retained.length, 3, 'release media, not the watched answer results')
    for (let index = 0; index < 3; index++) {
      assert.equal(retained[index], original[index])
      assert.equal(retained[index].recordingBlob, null, 'release media for every answer of a fully completed exam together')
      assert.equal(retained[index].transcript, TRANSCRIPT)
    }
    assert.deepEqual(Array.from(retained, answer => answer.scoringResult.totalScore), [78, 78, 86])
    assert.equal(other.recordingBlob, otherBlob, 'another unfinished exam must keep its recording')
    assert.equal(store.pendingAnswers[0], other)
  } finally {
    retryScoring.resolve(SCORE)
    await store.waitForPendingProcessing(oldId)
  }
})

test('web rejected start preserves the old exam, current recording and processing task', async () => {
  const upload = deferred()
  let starts = 0
  const store = await createStore({
    start: async () => { if (++starts > 1) throw new Error('start unavailable'); return { examId: 'web-original' } },
    upload: () => upload.promise
  })
  const blob = new Blob(['keep this recording']), old = await store.submitAnswer(blob)
  try {
    await assert.rejects(store.initExam([{ id: 'replacement' }]), /start unavailable/)
    assert.equal(store.examId, 'web-original')
    assert.equal(store.currentQuestion.id, 'q1')
    assert.equal(store.answers[0], old)
    assert.equal(store.recordingBlob, blob)
    const waiting = observe(store.waitForPendingProcessing('web-original'))
    await flush()
    assert.equal(waiting.done, false)
  } finally {
    upload.resolve({})
    await store.waitForPendingProcessing('web-original')
  }
})

test('web account change, explicit exit and Pinia reset discard archives and disallow old-answer retries', async () => {
  for (const mode of ['account-change', 'exit', 'pinia-reset']) {
    const upload = deferred(), storage = new Map([['token', 'owner-a']])
    let starts = 0, asrCalls = 0
    const store = await createStore({
      start: async () => ({ examId: `${mode}-${++starts}` }), upload: () => upload.promise,
      transcribe: async () => { asrCalls++; return { transcript: TRANSCRIPT } }
    }, { localStorage: { getItem: key => storage.get(key) || null } })
    const old = await store.submitAnswer(new Blob(['private recording'])), oldId = store.examId
    await store.initExam([{ id: 'new-question' }])
    try {
      assert.equal(store.getAnswersForExam(oldId)[0], old)
      if (mode === 'account-change') storage.set('token', 'owner-b')
      else if (mode === 'exit') store.exitExam()
      else store.$reset()
      assert.equal(store.getAnswersForExam(oldId).length, 0)
      assert.equal(store.pendingAnswers.length, 0)
      assert.equal(await store.retryAnswer(old), null)
      upload.resolve({})
      await store.waitForPendingProcessing(oldId)
      assert.equal(asrCalls, 0, `${mode}: clearing ownership must stop the next phase even if the token is unchanged`)
      assert.equal(store.getAnswersForExam(oldId).length, 0)
      assert.equal(store.pendingAnswers.length, 0)
    } finally {
      upload.resolve({})
      await store.waitForPendingProcessing(oldId)
    }
  }
})

test('web a late start response cannot restore an exam after exit under the same token', async () => {
  const starting = deferred()
  let starts = 0
  const store = await createStore({ start: () => ++starts === 1 ? Promise.resolve({ examId: 'old-web' }) : starting.promise })
  const beginning = observe(store.initExam([{ id: 'late-question' }]))
  store.exitExam()
  starting.resolve({ examId: 'late-web' })
  await beginning.promise
  assert.equal(beginning.error?.code, 'STALE_SESSION')
  assert.equal(store.examId, null)
  assert.equal(store.pendingAnswers.length, 0)
})
