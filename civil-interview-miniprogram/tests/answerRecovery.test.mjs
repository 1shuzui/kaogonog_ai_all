import test from 'node:test'
import assert from 'node:assert/strict'
import { readFile } from 'node:fs/promises'
import vm from 'node:vm'
import { hasFinalScore } from '../src/utils/answerStatus.js'

async function createStore(api) {
  const code = await readFile(new URL('../src/stores/exam.js', import.meta.url), 'utf8')
  const module = new vm.SourceTextModule(code)
  const mocks = {
    pinia: { defineStore: (_, options) => options },
    '../api/exam': { startExam() {}, completeExam() {}, uploadRecording: api.upload },
    '../api/scoring': { evaluateAnswer: api.evaluate, transcribeAudio: api.transcribe },
    '../utils/mediaUpload': { prepareMediaForUpload: async (filePath, mediaType) => ({ filePath, mediaType }) },
    '../utils/scoring': { normalizeResult: value => value }
  }
  await module.link(name => {
    const exports = mocks[name]
    return new vm.SyntheticModule(Object.keys(exports), function () {
      for (const [key, value] of Object.entries(exports)) this.setExport(key, value)
    })
  })
  await module.evaluate()
  const options = module.namespace.useExamStore
  const store = Object.assign(options.state(), options.actions)
  for (const [key, getter] of Object.entries(options.getters)) {
    Object.defineProperty(store, key, { get: () => getter(store) })
  }
  store.examId = 'exam-retry'
  store.questions = [{ id: 'q1', stem: '题目' }]
  return store
}

test('a timeout retains the transcript and retry does not upload or transcribe again', async () => {
  let uploads = 0, transcriptions = 0, evaluations = 0
  const transcript = '首先了解群众诉求，协调资源解决问题，最后跟进落实。'
  const store = await createStore({
    upload: async () => { uploads += 1 },
    transcribe: async () => { transcriptions += 1; return { transcript, asrMeta: { status: 'ok' } } },
    evaluate: async data => {
      evaluations += 1
      assert.equal(data.transcript, transcript)
      if (evaluations === 1) throw new Error('timeout')
      return { totalScore: 78, maxScore: 100 }
    }
  })
  await assert.rejects(store.submitCurrentAnswer({ filePath: 'record.mp3' }), /文字稿已保留/)
  assert.equal(store.answers[0].transcript, transcript)
  assert.equal(store.latestTranscript, transcript)
  const result = await store.submitCurrentAnswer({ filePath: 'record.mp3' })
  assert.equal(result.processingStatus, 'completed')
  assert.equal(result.scoringResult.totalScore, 78)
  assert.equal(uploads, 1)
  assert.equal(transcriptions, 1)
  assert.equal(evaluations, 2)
})

test('pending media records are distinct from genuine zero scores', () => {
  assert.equal(hasFinalScore({ mediaRecord: { fileUrl: '/uploads/answer.mp3' } }), false)
  assert.equal(hasFinalScore(null), false)
  assert.equal(hasFinalScore({ totalScore: null }), false)
  assert.equal(hasFinalScore({ totalScore: 0 }), true)
  assert.equal(hasFinalScore({ totalScore: 75 }), true)
})

test('retained transcripts reach scoring unchanged without another upload or ASR', async () => {
  const transcript = '第一，了解实际情况。第二，协调解决诉求。第三，及时回访。'
  let evaluations = 0
  const store = await createStore({
    upload: async () => assert.fail('retained transcript must not upload media again'),
    transcribe: async () => assert.fail('retained transcript must not invoke ASR again'),
    evaluate: async data => { evaluations++; assert.equal(data.transcript, transcript); return { totalScore: 78, maxScore: 100 } }
  })
  const result = await store.submitCurrentAnswer({ transcript })
  assert.equal(result.transcript, transcript)
  assert.equal(result.processingStatus, 'completed')
  assert.equal(evaluations, 1)
  await assert.rejects(store.submitCurrentAnswer({ transcript: '字'.repeat(5001) }), /5000/)
})

test('only audio and video modes are accepted; legacy text mode returns to audio', async () => {
  const store = await createStore({})
  for (const [input, expected] of [['audio', 'audio'], ['video', 'video'], ['text', 'audio'], [undefined, 'audio']]) {
    store.setMediaMode(input)
    assert.equal(store.mediaMode, expected)
  }
})

test('media-only room submits recorded files and confirms before skipping empty answers', async () => {
  const source = await readFile(new URL('../src/pages/exam/room.vue', import.meta.url), 'utf8')
  const calls = []
  let confirmations = 0
  const context = {
    examStore: { loading: false, isLastQuestion: false, submitCurrentAnswer: async payload => { calls.push(payload); return {} } },
    finishingExam: { value: false }, isJiangsuReading: { value: false },
    submittingAnswer: { value: false }, pauseCaptureClock() {}, resumeCaptureClock() {},
    recording: { value: false }, videoRecording: { value: false },
    currentMedia: { value: { filePath: 'record.mp3', mediaType: 'audio' } }, recordedFile: { value: 'record.mp3' },
    textAnswer: { value: '旧文字输入' },
    confirmSkipCurrentQuestion: async () => { confirmations++; return false },
    stopActiveCaptureAsync: async () => {}, buildTimingMeta: () => ({}),
    continueAfterSubmittedAnswer: async () => {}, syncUsageAndTrial: async () => {},
    showLoading() {}, hideLoading() {}, toast: text => assert.fail(text)
  }
  const loadFunction = name => {
    const declaration = source.match(new RegExp(`async function ${name}\\([^]*?^}`, 'm'))?.[0]
    assert.ok(declaration)
    return vm.runInNewContext(`(${declaration})`, context)
  }
  await loadFunction('submitAnswer')()
  await loadFunction('submitCurrentAnswerForExit')()
  assert.equal(calls.length, 2)
  assert.ok(calls.every(call => call.filePath === 'record.mp3' && !('transcript' in call)))
  context.currentMedia.value = { filePath: '', mediaType: '' }
  await loadFunction('submitAnswer')()
  assert.equal(confirmations, 1)
  assert.equal(calls.length, 2)
  assert.equal(await loadFunction('submitCurrentAnswerForExit')(), null)
})

test('audio and video transcription both allow a cold ASR model to finish', async () => {
  const calls = []
  const code = await readFile(new URL('../src/api/scoring.js', import.meta.url), 'utf8')
  const module = new vm.SourceTextModule(code)
  await module.link(() => new vm.SyntheticModule(['request', 'uploadFile'], function () {
    this.setExport('request', options => options)
    this.setExport('uploadFile', options => { calls.push(options); return Promise.resolve({}) })
  }))
  await module.evaluate()
  for (const mediaType of ['audio', 'video']) {
    await module.namespace.transcribeAudio('record.mp3', { mediaType, questionId: 'q1', examId: 'exam1' })
    assert.equal(calls.at(-1).timeout, 120000)
    assert.deepEqual(calls.at(-1).formData, { mediaType, questionId: 'q1', examId: 'exam1' })
  }
})
