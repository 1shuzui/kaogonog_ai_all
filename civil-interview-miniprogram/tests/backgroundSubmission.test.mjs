import test from 'node:test'
import assert from 'node:assert/strict'
import { readFile } from 'node:fs/promises'
import vm from 'node:vm'

const TRANSCRIPT = '第一题：先了解实际情况，再协调资源解决问题，最后回访。'
const SCORE = { totalScore: 78, maxScore: 100 }
const ref = value => ({ value })
// Drain ready promise jobs, never wait for elapsed wall-clock time.
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
  const context = vm.createContext({ uni: { getStorageSync: key => key === 'token' ? 'test-session-a' : '' }, ...runtime })
  const module = new vm.SourceTextModule(source, { context })
  const mocks = {
    pinia: { defineStore: (_, options) => options },
    '../api/exam': {
      startExam: api.start || (async () => ({ examId: 'background-mini' })), completeExam: api.complete || (async () => ({})),
      uploadRecording: api.upload || (async () => ({}))
    },
    '../api/scoring': {
      transcribeAudio: api.transcribe || (async () => ({ transcript: TRANSCRIPT, asrMeta: { status: 'ok' } })),
      evaluateAnswer: api.evaluate || (async () => SCORE)
    },
    '../utils/mediaUpload': { prepareMediaForUpload: async (filePath, mediaType) => ({ filePath, mediaType }) },
    '../utils/scoring': { normalizeResult: value => value },
    '../utils/constants': { TOKEN_STORAGE_KEY: 'token' }
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
  for (const [key, getter] of Object.entries(options.getters)) Object.defineProperty(store, key, { get: () => getter(store) })
  await store.startFromQuestions(['q1', 'q2', 'q3'].map(id => ({ id, stem: id, fullExamTimingMode: 'jiangsu_5_15' })), 'fullExam')
  return store
}

test('mini room submits with waitForProcessing:false and freezes timing before the recorder flush', async () => {
  const stopped = deferred(), upload = deferred(), asr = deferred(), scoring = deferred()
  const store = await createStore({ upload: () => upload.promise, transcribe: () => asr.promise, evaluate: () => scoring.promise })
  const payloads = [], errors = []
  const submit = store.submitCurrentAnswer
  store.submitCurrentAnswer = function (payload) { payloads.push(payload); return submit.call(this, payload) }
  let now = 130000
  const source = await readFile(new URL('../src/pages/exam/room.vue', import.meta.url), 'utf8')
  const context = vm.createContext({
    examStore: store, finishingExam: ref(false), isJiangsuReading: ref(false), isJiangsuFullExamTiming: ref(true),
    submittingAnswer: ref(false), timerPausedAt: null, timerPhase: 'answering', timerDeadline: 1030000,
    recording: ref(true), videoRecording: ref(false), recordedFile: ref('q1.mp3'),
    currentMedia: ref({ filePath: 'q1.mp3', mediaType: 'audio' }),
    questionStartedAt: ref(100000), overtimeSeconds: ref(0),
    JIANGSU_READING_SECONDS: 300, JIANGSU_ANSWER_SECONDS: 900,
    Date: class extends Date { static now() { return now } },
    stopRecordAsync: () => stopped.promise, stopVideoRecord: async () => {},
    continueAfterSubmittedAnswer: async () => { store.goNext() },
    showLoading() {}, hideLoading() {}, toast: text => errors.push(text),
    confirmSkipCurrentQuestion: async () => false
  })
  for (const name of ['currentUsageSeconds', 'standardQuestionSeconds', 'buildTimingMeta', 'pauseCaptureClock', 'resumeCaptureClock']) {
    context[name] = extractSFC(source, name, context)
  }
  const pending = observe(extractSFC(source, 'submitAnswer', context)())
  // Simulate a 60-second device flush without sleeping or allowing a network request.
  now += 60000
  stopped.resolve('q1.mp3')
  try {
    await flush()
    assert.equal(pending.error, null)
    assert.deepEqual(errors, [])
    assert.equal(payloads.length, 1)
    assert.deepEqual({
      waitForProcessing: payloads[0].waitForProcessing,
      actualSeconds: payloads[0].timingMeta.actualSeconds,
      standardSeconds: payloads[0].timingMeta.standardSeconds,
      questionIndex: store.currentIndex, returned: pending.done
    }, { waitForProcessing: false, actualSeconds: 30, standardSeconds: 1200, questionIndex: 1, returned: true },
    'upload, ASR and scoring must not lock the room or be charged to the submitted question')
  } finally {
    stopped.resolve('q1.mp3')
    upload.resolve({})
    asr.resolve({ transcript: TRANSCRIPT, asrMeta: { status: 'ok' } })
    scoring.resolve(SCORE)
    await pending.promise
    await store.waitForPendingProcessing()
  }
})

test('mini continueAfterSubmittedAnswer advances before usage resolves and preserves the shared Jiangsu answer time', async () => {
  const usage = deferred(), store = await createStore()
  const answer = { examId: store.examId, questionId: 'q1', questionIndex: 0, answerTiming: { actualSeconds: 30 }, processingStatus: 'queued' }
  store.answers.push(answer)
  const usageCalls = [], source = await readFile(new URL('../src/pages/exam/room.vue', import.meta.url), 'utf8')
  const context = vm.createContext({
    examStore: store, isJiangsuFullExamTiming: ref(true), isFullExamSource: ref(true),
    timerPausedAt: null, timerPhase: 'answering', timerDeadline: 910000,
    phase: ref('answering'), prepLeft: ref(0), answerLeft: ref(780), overtimeSeconds: ref(0),
    questionStartedAt: ref(100000), questionBookIndex: ref(0),
    recording: ref(false), recordedFile: ref('q1.mp3'), videoRecording: ref(false),
    recordedVideoFile: ref(''), selectedMediaType: ref('audio'),
    question: { get value() { return store.currentQuestion } },
    userStore: { preferences: { defaultPrepTime: 90, defaultAnswerTime: 180 } },
    JIANGSU_READING_SECONDS: 300, JIANGSU_ANSWER_SECONDS: 900,
    Date: class extends Date { static now() { return 130000 } },
    reportedQuestionKeys: new Set(),
    reportUsage: payload => { usageCalls.push(payload); return usage.promise },
    subscriptionStore: { refresh: async () => {} }, toast() {}
  })
  for (const name of ['currentUsageSeconds', 'usageType', 'syncUsageAndTrial', 'resetAnswerInputState', 'resetQuestionState']) {
    context[name] = extractSFC(source, name, context)
  }
  const pending = observe(extractSFC(source, 'continueAfterSubmittedAnswer', context)(answer, false))
  try {
    await flush()
    assert.equal(pending.error, null)
    assert.equal(usageCalls.length, 1)
    assert.equal(usageCalls[0].usageSeconds, 30)
    assert.deepEqual({ phase: context.phase.value, reading: context.prepLeft.value, answering: context.answerLeft.value },
      { phase: 'answering', reading: 0, answering: 780 }, 'do not restart 5-minute reading or 15-minute answering at the next question')
    assert.deepEqual({ questionIndex: store.currentIndex, media: context.recordedFile.value, returned: pending.done },
      { questionIndex: 1, media: '', returned: true }, 'an unresolved usage request must not delay the next question')
    assert.equal(store.answers[0], answer, 'resetting the room must retain the queued answer')
  } finally {
    usage.resolve({})
    await pending.promise
  }
})

test('mini duplicate submission keeps the queued answer attached; late failure and retry cannot overwrite the next question', async () => {
  const upload = deferred(), asr = deferred(), scoring = deferred()
  let uploads = 0, transcriptions = 0, retry = false
  const store = await createStore({
    upload: () => { uploads++; return upload.promise },
    transcribe: () => { transcriptions++; return asr.promise },
    evaluate: () => retry ? Promise.resolve(SCORE) : scoring.promise
  })
  const payload = { filePath: 'q1.mp3', timingMeta: { actualSeconds: 32, standardSeconds: 1200, overtimeSeconds: 0 }, waitForProcessing: false }
  await store.submitCurrentAnswer(payload)
  await store.submitCurrentAnswer(payload)
  const queued = store.answers.find(answer => answer.questionId === 'q1')
  const savedCount = store.answers.length
  store.goNext()
  store.latestTranscript = '第二题正在作答'
  store.latestResult = null
  upload.resolve({})
  asr.resolve({ transcript: TRANSCRIPT, asrMeta: { status: 'ok' } })
  await flush()
  scoring.reject(new Error('mock scoring timeout'))
  await store.waitForPendingProcessing()
  const failedStatus = queued.processingStatus
  const retainedTranscript = queued.transcript
  retry = true
  await store.queueAnswerProcessing(queued)
  assert.deepEqual({ index: store.currentIndex, transcript: store.latestTranscript, result: store.latestResult, loading: store.loading },
    { index: 1, transcript: '第二题正在作答', result: null, loading: false }, 'late q1 work must not mutate the q2 view')
  assert.equal(queued.filePath, 'q1.mp3')
  assert.equal(queued.answerTiming.actualSeconds, 32, 'the saved question duration remains fixed through failure and retry')
  assert.equal(queued.processingStatus, 'completed')
  assert.deepEqual({ savedCount, uploads, transcriptions, failedStatus, retainedTranscript },
    { savedCount: 1, uploads: 1, transcriptions: 1, failedStatus: 'failed', retainedTranscript: TRANSCRIPT },
    'deduplicating the task must also retain its answer object; retry must reuse the saved transcript')
})

test('mini finish closes immediately, then refreshes the captured exam only after its queued scoring finishes', async () => {
  const scoring = deferred(), close = deferred(), calls = []
  let graded = false
  const store = await createStore({
    evaluate: () => scoring.promise,
    complete: examId => { calls.push({ examId, graded }); return close.promise }
  })
  const answer = await store.submitCurrentAnswer({ filePath: 'q1.mp3', waitForProcessing: false })
  await flush()
  const originalExamId = store.examId
  const pending = observe(Promise.resolve(store.finish()))
  const immediately = calls.map(call => ({ ...call }))
  try {
    close.resolve({})
    await flush()
    const beforeScoring = calls.length
    store.examId = 'subsequent-mini-exam'
    graded = true
    scoring.resolve(SCORE)
    await store.waitForPendingProcessing()
    await pending.promise
    await flush()
    assert.equal(pending.error, null)
    assert.deepEqual({ immediately, beforeScoring, afterScoring: calls }, {
      immediately: [{ examId: originalExamId, graded: false }], beforeScoring: 1,
      afterScoring: [{ examId: originalExamId, graded: false }, { examId: originalExamId, graded: true }]
    }, 'end time is saved before grading and the old exam remains the target of the background refresh')
    assert.equal(store.examId, 'subsequent-mini-exam')
    assert.ok(store.answers.includes(answer), 'finish must retain the queued media/transcript')
    assert.equal(answer.scoringResult.totalScore, 78)
  } finally {
    close.resolve({})
    scoring.resolve(SCORE)
    await pending.promise
  }
})

test('mini final answer opens the result page before usage/finalization resolve and retains queued answers', async () => {
  const usage = deferred(), queue = deferred(), navigation = []
  let finalizations = 0
  const answer = { examId: 'mini-finishing', questionId: 'q3', processingStatus: 'scoring' }
  const store = {
    examId: answer.examId, answers: [answer],
    finish: () => { finalizations++; return queue.promise },
    reset() { this.examId = ''; this.answers = [] }
  }
  const source = await readFile(new URL('../src/pages/exam/room.vue', import.meta.url), 'utf8')
  const context = vm.createContext({
    examStore: store, syncUsageAndTrial: () => usage.promise,
    timer: null, clearInterval() {},
    uni: { redirectTo: ({ url }) => navigation.push(url) }
  })
  const pending = observe(extractSFC(source, 'continueAfterSubmittedAnswer', context)(answer, true))
  await flush()
  const beforeBackground = { navigation: [...navigation], finalizations, returned: pending.done }
  usage.resolve({})
  queue.resolve({})
  await pending.promise
  assert.equal(pending.error, null)
  assert.deepEqual({ ...beforeBackground, retainedAnswer: store.answers.includes(answer) }, {
    navigation: ['/pages/result/index?examId=mini-finishing&questionId=q3'], finalizations: 1, returned: true, retainedAnswer: true
  }, 'opening the result page must not wait for external requests or clear the store they still need')
})

test('mini account changes between upload/ASR stages prevent every subsequent request under the new token', async () => {
  const outcomes = []
  for (const switchAfter of ['upload', 'asr']) {
    const upload = deferred(), asr = deferred(), calls = []
    const storage = new Map([['token', 'test-account-a']])
    const record = stage => calls.push({ stage, token: storage.get('token') })
    const store = await createStore({
      upload: () => { record('upload'); return upload.promise },
      transcribe: () => { record('asr'); return asr.promise },
      evaluate: async () => { record('score'); return SCORE }
    }, { uni: { getStorageSync: key => storage.get(key) || '' } })
    await store.submitCurrentAnswer({ filePath: 'account-a.mp3', waitForProcessing: false })
    await flush()
    if (switchAfter === 'asr') {
      upload.resolve({})
      await flush()
    }
    storage.set('token', 'test-account-b')
    upload.resolve({})
    asr.resolve({ transcript: TRANSCRIPT, asrMeta: { status: 'ok' } })
    await store.waitForPendingProcessing()
    outcomes.push({ switchAfter, calls })
  }
  assert.deepEqual(outcomes, [
    { switchAfter: 'upload', calls: [{ stage: 'upload', token: 'test-account-a' }] },
    { switchAfter: 'asr', calls: [{ stage: 'upload', token: 'test-account-a' }, { stage: 'asr', token: 'test-account-a' }] }
  ], 'a resolved old request must not continue the answer pipeline using the newly logged-in account')
})

test('mini delayed ticks carry Jiangsu reading overshoot forward and exclude only the local capture pause across questions', async () => {
  let now = 1000, nextTimerId = 0
  const timers = new Map(), usage = deferred()
  const source = await readFile(new URL('../src/pages/exam/room.vue', import.meta.url), 'utf8')
  const context = vm.createContext({
    Date: class extends Date { static now() { return now } },
    setInterval: callback => { const id = ++nextTimerId; timers.set(id, callback); return id },
    clearInterval: id => timers.delete(id),
    timer: null, timerPhase: 'reading', timerDeadline: 301000, timerPausedAt: null,
    phase: ref('reading'), prepLeft: ref(300), answerLeft: ref(900), overtimeSeconds: ref(0), questionStartedAt: ref(1000),
    isJiangsuFullExamTiming: ref(true), recording: ref(false), videoRecording: ref(false),
    recordedFile: ref('q1.mp3'), recordedVideoFile: ref(''), selectedMediaType: ref('audio'),
    examStore: { currentIndex: 0, goNext() { this.currentIndex++; return true } },
    syncUsageAndTrial: () => usage.promise, toast() {}
  })
  for (const name of ['startTimer', 'pauseCaptureClock', 'resumeCaptureClock', 'currentUsageSeconds', 'resetAnswerInputState', 'continueAfterSubmittedAnswer']) {
    context[name] = extractSFC(source, name, context)
  }
  const tickAt = time => { now = time; for (const callback of [...timers.values()]) callback() }
  context.startTimer()
  try {
    tickAt(301750) // First delivered tick arrives 750ms after the reading deadline.
    tickAt(421250)
    assert.deepEqual({ phase: context.phase.value, reading: context.prepLeft.value, answering: context.answerLeft.value },
      { phase: 'answering', reading: 0, answering: 780 }, 'reading overshoot must consume the same shared 5+15 budget')
    now = 421450
    context.pauseCaptureClock()
    const submittedSeconds = context.currentUsageSeconds()
    tickAt(481450) // Slow device finalization, not answer time.
    assert.equal(context.currentUsageSeconds(), submittedSeconds)
    assert.equal(context.answerLeft.value, 780)
    context.resumeCaptureClock()
    await context.continueAfterSubmittedAnswer({ questionId: 'q1' }, false)
    tickAt(482200) // Another 750ms of real answer time after advancing.
    assert.deepEqual({ index: context.examStore.currentIndex, phase: context.phase.value, remaining: context.answerLeft.value, usage: context.currentUsageSeconds() },
      { index: 1, phase: 'answering', remaining: 779, usage: 1 }, 'resume must preserve fractional active time without resetting the shared answer budget')
  } finally {
    usage.resolve({})
    context.clearInterval(context.timer)
  }
})

test('mini ASR automatic retry never reuses another account after a failed or placeholder response', async () => {
  const outcomes = []
  for (const firstResult of ['network-error', 'placeholder']) {
    const asr = deferred(), calls = [], storage = new Map([['token', 'test-account-a']])
    const record = stage => calls.push({ stage, token: storage.get('token') })
    let attempts = 0
    const store = await createStore({
      upload: async () => { record('upload'); return {} },
      transcribe: () => {
        record('asr')
        return ++attempts === 1 ? asr.promise : Promise.resolve({ transcript: TRANSCRIPT, asrMeta: { status: 'ok' } })
      },
      evaluate: async () => { record('score'); return SCORE }
    }, { uni: { getStorageSync: key => storage.get(key) || '' } })
    await store.submitCurrentAnswer({ filePath: 'account-a.mp3', waitForProcessing: false })
    await flush()
    assert.equal(attempts, 1, 'switch accounts while the first ASR request is actually in flight')
    storage.set('token', 'test-account-b')
    if (firstResult === 'network-error') asr.reject(new Error('mock ASR connection failure'))
    else asr.resolve({ transcript: '', needsRetry: true, asrMeta: { status: 'asr_unavailable' } })
    await store.waitForPendingProcessing()
    outcomes.push({ firstResult, calls })
  }
  assert.deepEqual(outcomes, ['network-error', 'placeholder'].map(firstResult => ({
    firstResult, calls: [{ stage: 'upload', token: 'test-account-a' }, { stage: 'asr', token: 'test-account-a' }]
  })), 'session validation must guard automatic retry attempts as well as the next pipeline stage')
})

test('mini keeps the previous exam task and failed recording reachable across a successful new start', async () => {
  const upload = deferred(), starting = deferred()
  let starts = 0, uploads = 0, evaluations = 0
  const store = await createStore({
    start: () => ++starts === 2 ? starting.promise : Promise.resolve({ examId: `mini-${starts}` }),
    upload: () => { uploads++; return upload.promise },
    evaluate: async () => { if (++evaluations === 1) throw new Error('model offline'); return SCORE }
  })
  const old = await store.submitCurrentAnswer({ filePath: 'old.mp3', waitForProcessing: false }), oldId = store.examId
  const beginning = observe(store.startFromQuestions([{ id: 'new-question' }]))
  try {
    assert.equal(store.answers[0], old)
    starting.resolve({ examId: 'mini-2' })
    await beginning.promise
    assert.equal(beginning.error, null)
    assert.equal(store.answers.length, 0)
    assert.equal(store.getAnswersForExam(oldId)[0], old)
    assert.equal(store.pendingAnswers[0], old)
    const waiting = observe(store.waitForPendingProcessing(oldId))
    await flush()
    assert.equal(waiting.done, false, 'new exams must not clear a previous exam processing map')
    store.latestTranscript = '新场当前作答'
    upload.resolve({})
    await waiting.promise
    assert.equal(old.processingStatus, 'failed')
    assert.equal(old.filePath, 'old.mp3')
    assert.equal(old.transcript, TRANSCRIPT)
    assert.equal(store.pendingAnswers[0], old)
    assert.equal(await store.retryAnswer({ ...old }), null)
    const retry = store.retryAnswer(old)
    await Promise.all([retry, store.retryAnswer(old)])
    assert.equal(old.processingStatus, 'completed')
    assert.equal(store.getAnswersForExam(oldId)[0], old)
    assert.equal(store.pendingAnswers.length, 0)
    assert.equal(store.getAnswersForExam('unknown').length, 0)
    assert.equal(store.latestTranscript, '新场当前作答')
    assert.equal(store.latestResult, null)
    assert.deepEqual({ uploads, evaluations }, { uploads: 1, evaluations: 2 })
    await store.startFromQuestions([{ id: 'third-question' }])
    assert.equal(store.getAnswersForExam(oldId)[0], old, 'a subsequent start must not erase a completed archive from an open result page')
    assert.equal(store.pendingAnswers.length, 0, 'completed archives are retained results, not pending task reminders')
  } finally {
    starting.resolve({ examId: 'mini-2' })
    upload.resolve({})
    await beginning.promise
    await store.waitForPendingProcessing(oldId)
  }
})

test('mini archived result views retain already-completed and late-completed answers until session reset', async () => {
  const scoring = deferred()
  let starts = 0
  const store = await createStore({
    start: async () => ({ examId: `retained-mini-${++starts}` }),
    evaluate: ({ questionId }) => questionId === 'q2' ? scoring.promise : Promise.resolve(SCORE)
  })
  const oldId = store.examId
  const first = await store.submitCurrentAnswer({ filePath: 'first.mp3', waitForProcessing: false })
  await store.waitForPendingProcessing(oldId)
  assert.equal(first.processingStatus, 'completed')
  store.goNext()
  const second = await store.submitCurrentAnswer({ filePath: 'second.mp3', waitForProcessing: false })
  try {
    await store.startFromQuestions([{ id: 'next-exam-question' }])
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
    await store.startFromQuestions([{ id: 'another-exam-question' }])
    const after = store.getAnswersForExam(oldId)
    assert.equal(after.length, 2, 'a later start cannot empty the watched exam result set or duplicate its answers')
    assert.equal(after[0], first)
    assert.equal(after[1], second)
    assert.equal(after[0].scoringResult.totalScore, 78)
    assert.equal(after[1].scoringResult.totalScore, 86)
    store.reset()
    assert.equal(store.getAnswersForExam(oldId).length, 0)
    assert.equal(store.pendingAnswers.length, 0)
    assert.equal(await store.retryAnswer(first), null, 'reset also releases ownership of completed archived answers')
  } finally {
    scoring.resolve(SCORE)
    await store.waitForPendingProcessing(oldId)
  }
})

test('mini resolved scoring responses need a finite score; invalid responses retain retryable media/transcript and genuine zero succeeds', async () => {
  const invalidResults = [undefined, null, {}, { totalScore: null }, { totalScore: '' }, { totalScore: ' ' },
    { totalScore: NaN }, { totalScore: Infinity }, { totalScore: 'not-a-score' }, { score: -Infinity },
    { totalScore: false }, { score: [] }]
  for (const [index, invalidResult] of invalidResults.entries()) {
    const scoring = deferred()
    let uploads = 0, transcriptions = 0, evaluations = 0
    const store = await createStore({
      upload: async () => { uploads++; return {} },
      transcribe: async () => { transcriptions++; return { transcript: TRANSCRIPT, asrMeta: { status: 'ok' } } },
      evaluate: async payload => {
        assert.equal(payload.transcript, TRANSCRIPT)
        return ++evaluations === 1 ? scoring.promise : index % 2 ? { score: 0 } : { totalScore: 0 }
      }
    })
    const answer = await store.submitCurrentAnswer({ filePath: 'retained.mp3', waitForProcessing: false })
    scoring.resolve(invalidResult) // A fulfilled HTTP response, not a rejected network request.
    await store.waitForPendingProcessing()
    assert.equal(answer.processingStatus, 'failed', `invalid successful response ${index} must remain retryable`)
    assert.equal(answer.transcript, TRANSCRIPT)
    assert.equal(answer.filePath, 'retained.mp3')
    assert.equal(answer.scoringResult, null)
    assert.equal(store.latestResult, null)
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

test('mini archives all three answers of a partly failed exam and releases media only after the whole exam completes', async () => {
  const retryScoring = deferred(), original = []
  let starts = 0, thirdAttempts = 0, rejectStart = false
  const store = await createStore({
    start: async () => {
      if (rejectStart) throw new Error('start unavailable')
      return { examId: `three-mini-${++starts}` }
    },
    evaluate: async ({ questionId }) => {
      if (questionId === 'other-failed' || (questionId === 'q3' && ++thirdAttempts === 1)) throw new Error('model offline')
      return questionId === 'q3' ? retryScoring.promise : SCORE
    }
  })
  const oldId = store.examId
  for (let index = 0; index < 3; index++) {
    original.push(await store.submitCurrentAnswer({
      filePath: `recording-${index}.mp4`, audioFilePath: `recording-${index}.mp3`, mediaType: 'video', waitForProcessing: false
    }))
    await store.waitForPendingProcessing(oldId)
    store.goNext()
  }
  assert.deepEqual(original.map(answer => answer.processingStatus), ['completed', 'completed', 'failed'])
  try {
    await store.startFromQuestions([{ id: 'other-failed' }])
    const archived = store.getAnswersForExam(oldId)
    assert.equal(archived.length, 3, 'two completed answers must accompany the failed answer into the archive')
    for (let index = 0; index < 3; index++) {
      assert.equal(archived[index], original[index])
      assert.equal(archived[index].filePath, `recording-${index}.mp4`)
      assert.equal(archived[index].audioFilePath, `recording-${index}.mp3`)
    }
    assert.equal(archived[0].scoringResult.totalScore, 78)
    assert.equal(archived[1].scoringResult.totalScore, 78)
    assert.equal(store.pendingAnswers.length, 1)
    assert.equal(store.pendingAnswers[0], original[2])
    const other = await store.submitCurrentAnswer({ filePath: 'other.mp3', waitForProcessing: false })
    await store.waitForPendingProcessing()
    const retry = store.retryAnswer(original[2])
    await flush()
    await store.startFromQuestions([{ id: 'new-question' }])
    for (let index = 0; index < 3; index++) {
      assert.equal(original[index].filePath, `recording-${index}.mp4`)
      assert.equal(original[index].audioFilePath, `recording-${index}.mp3`)
    }
    retryScoring.resolve({ totalScore: 86, maxScore: 100 })
    await retry
    assert.equal(store.pendingAnswers.length, 1)
    assert.equal(store.pendingAnswers[0], other)
    for (let index = 0; index < 3; index++) assert.equal(original[index].filePath, `recording-${index}.mp4`, 'completion itself must not dispose media')
    rejectStart = true
    await assert.rejects(store.startFromQuestions([{ id: 'rejected-question' }]), /start unavailable/)
    for (let index = 0; index < 3; index++) assert.equal(original[index].filePath, `recording-${index}.mp4`, 'failed starts cannot collect archived media')
    rejectStart = false
    await store.startFromQuestions([{ id: 'next-question' }])
    const retained = store.getAnswersForExam(oldId)
    assert.equal(retained.length, 3, 'release media, not the watched answer results')
    for (let index = 0; index < 3; index++) {
      assert.equal(retained[index], original[index])
      assert.equal(retained[index].filePath, '', 'release video references for the whole completed exam')
      assert.equal(retained[index].audioFilePath, '', 'release extracted audio references for the whole completed exam')
      assert.equal(retained[index].transcript, TRANSCRIPT)
    }
    assert.deepEqual(Array.from(retained, answer => answer.scoringResult.totalScore), [78, 78, 86])
    assert.equal(other.filePath, 'other.mp3', 'another unfinished exam must keep its recording')
    assert.equal(store.pendingAnswers[0], other)
  } finally {
    retryScoring.resolve(SCORE)
    await store.waitForPendingProcessing(oldId)
  }
})

test('mini rejected start preserves the old exam, current recording and processing task', async () => {
  const upload = deferred()
  let starts = 0
  const store = await createStore({
    start: async () => { if (++starts > 1) throw new Error('start unavailable'); return { examId: 'mini-original' } },
    upload: () => upload.promise
  })
  const old = await store.submitCurrentAnswer({ filePath: 'original.mp3', waitForProcessing: false })
  try {
    await assert.rejects(store.startFromQuestions([{ id: 'replacement' }]), /start unavailable/)
    assert.equal(store.examId, 'mini-original')
    assert.equal(store.currentQuestion.id, 'q1')
    assert.equal(store.answers[0], old)
    const waiting = observe(store.waitForPendingProcessing('mini-original'))
    await flush()
    assert.equal(waiting.done, false)
  } finally {
    upload.resolve({})
    await store.waitForPendingProcessing('mini-original')
  }
})

test('mini account change and reset discard archives and disallow old-answer retries', async () => {
  for (const mode of ['account-change', 'reset']) {
    const upload = deferred(), storage = new Map([['token', 'owner-a']])
    let starts = 0, asrCalls = 0
    const store = await createStore({
      start: async () => ({ examId: `${mode}-${++starts}` }), upload: () => upload.promise,
      transcribe: async () => { asrCalls++; return { transcript: TRANSCRIPT, asrMeta: { status: 'ok' } } }
    }, { uni: { getStorageSync: key => storage.get(key) || '' } })
    const old = await store.submitCurrentAnswer({ filePath: 'private.mp3', waitForProcessing: false }), oldId = store.examId
    await store.startFromQuestions([{ id: 'new-question' }])
    try {
      assert.equal(store.getAnswersForExam(oldId)[0], old)
      if (mode === 'account-change') storage.set('token', 'owner-b')
      else store.reset()
      assert.equal(store.getAnswersForExam(oldId).length, 0)
      assert.equal(store.pendingAnswers.length, 0)
      assert.equal(await store.retryAnswer(old), null)
      upload.resolve({})
      await store.waitForPendingProcessing(oldId)
      assert.equal(asrCalls, 0, `${mode}: cleared tasks may not start another request`)
      assert.equal(store.getAnswersForExam(oldId).length, 0)
      assert.equal(store.pendingAnswers.length, 0)
    } finally {
      upload.resolve({})
      await store.waitForPendingProcessing(oldId)
    }
  }
})

test('mini a late start response cannot restore an exam after reset under the same token', async () => {
  const starting = deferred()
  let starts = 0
  const store = await createStore({ start: () => ++starts === 1 ? Promise.resolve({ examId: 'old-mini' }) : starting.promise })
  const beginning = observe(store.startFromQuestions([{ id: 'late-question' }]))
  store.reset()
  starting.resolve({ examId: 'late-mini' })
  await beginning.promise
  assert.equal(beginning.error?.code, 'STALE_SESSION')
  assert.equal(store.examId, '')
  assert.equal(store.pendingAnswers.length, 0)
})
