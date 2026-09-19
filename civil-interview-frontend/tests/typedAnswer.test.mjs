import test from 'node:test'
import assert from 'node:assert/strict'
import { readFile } from 'node:fs/promises'
import vm from 'node:vm'

test('web text answer retains its transcript after a model failure and retries without ASR', async () => {
  let calls = 0
  const source = await readFile(new URL('../src/stores/exam.js', import.meta.url), 'utf8')
  const module = new vm.SourceTextModule(source)
  const mocks = {
    pinia: { defineStore: (_, options) => options },
    '@/utils/constants': { EXAM_STATUS: { IDLE: 'idle', ANSWERING: 'answering', SUBMITTING: 'submitting', COMPLETED: 'completed' } },
    '@/api/exam': { startExam: async () => ({ examId: 'typed-exam' }), uploadRecording: () => assert.fail('no media upload') },
    '@/api/scoring': {
      transcribeAudio: () => assert.fail('no ASR'),
      evaluateAnswer: async payload => {
        assert.equal(payload.transcript, '先了解实际情况，再协调资源，最后回访。')
        if (++calls === 1) throw new Error('模型暂时超时')
        return { totalScore: 80, maxScore: 100 }
      }
    },
    '@/utils/scoringSupport': { getScoringUnavailableMessage() {}, isQuestionIdScoringSupported: () => true, normalizeScoringErrorMessage: text => text }
  }
  await module.link(name => new vm.SyntheticModule(Object.keys(mocks[name]), function () {
    for (const [key, value] of Object.entries(mocks[name])) this.setExport(key, value)
  }))
  await module.evaluate()
  const options = module.namespace.useExamStore
  const store = Object.assign(options.state(), options.actions)
  for (const [key, getter] of Object.entries(options.getters)) Object.defineProperty(store, key, { get: () => getter(store) })
  await store.initExam([{ id: 'q1' }])
  const answer = await store.submitAnswer(null, '先了解实际情况，再协调资源，最后回访。')
  await store.waitForPendingProcessing()
  assert.equal(answer.processingStatus, 'failed')
  assert.match(answer.transcript, /协调资源/)
  await store.processExamAnswer(answer)
  assert.equal(answer.scoringResult.totalScore, 80)
  assert.equal(calls, 2)
})
