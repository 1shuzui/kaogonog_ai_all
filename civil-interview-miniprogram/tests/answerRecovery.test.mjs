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
  await assert.rejects(store.submitCurrentAnswer({ filePath: 'record.mp3' }), /答案已保存/)
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
