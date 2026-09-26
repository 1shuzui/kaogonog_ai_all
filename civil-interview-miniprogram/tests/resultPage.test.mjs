import test from 'node:test'
import assert from 'node:assert/strict'
import { existsSync, readFileSync } from 'node:fs'
import vm from 'node:vm'
import { computed, ref, reactive, watch, effectScope, nextTick } from 'vue'
import * as constants from '../src/utils/constants.js'
import { hasFinalScore } from '../src/utils/answerStatus.js'
import { canUseLocalAnswers } from '../src/utils/resultAnswerSource.js'
import { getQuestionScorePair } from '../src/utils/scorePresentation.js'
import { createCancellation } from '../src/utils/cancellation.mjs'
import { resolveAnswerMedia } from '../../shared/answerMedia.mjs'
import { scoringExplanation } from '../../shared/scoringExplanation.mjs'

const source = readFileSync(new URL('../src/pages/result/index.vue', import.meta.url), 'utf8')
const script = source.match(/<script setup>([^]*?)<\/script>/)[1].replace(/^import .*$/gm, '')
const helperUrl = new URL('../src/utils/resultReview.mjs', import.meta.url)
const review = existsSync(helperUrl) ? await import(helperUrl.href) : {}
const scoringSource = readFileSync(new URL('../src/utils/scoring.js', import.meta.url), 'utf8').replace(/^import .*$/gm, '').replace(/^export /gm, '')
const scoring = vm.runInNewContext(`${scoringSource}\n;({ normalizeResult, normalizeImprovementSuggestion })`, constants)
const flush = async () => { await nextTick(); await new Promise(resolve => setImmediate(resolve)); await nextTick() }
function deferred() {
  let resolve, reject
  const promise = new Promise((yes, no) => { resolve = yes; reject = no })
  return { promise, resolve, reject }
}
const answer = (id, score = null) => ({ examId: 'exam-a', questionId: id, questionStem: `题目 ${id}`, transcript: `原文 ${id}`, scoringResult: score == null ? null : { totalScore: score, maxScore: 100 } })

function page(t, api = {}, local = []) {
  const scope = effectScope(), errors = [], requests = [], unload = [], shares = [], visible = ref(true)
  const store = reactive({ examId: 'exam-a', source: '', questions: [{ id: 'q1', stem: '题目 q1' }, { id: 'q2', stem: '题目 q2' }], answers: local,
    getAnswersForExam(id) { return this.answers.filter(item => item.examId === id) },
    retryAnswer: api.retry || (async () => null)
  })
  const request = options => {
    requests.push(options)
    if (options.url === '/scoring/evaluate') return api.evaluate(options)
    if (options.url.startsWith('/scoring/result/')) return api.saved(options)
    if (options.url.startsWith('/questions/')) return api.question(options)
    return api.history(options)
  }
  const context = vm.createContext({ computed, ref, watch, ...constants, ...scoring, ...review,
    hasFinalScore, canUseLocalAnswers, getQuestionScorePair, createCancellation, request, API_BASE: 'https://fixture.invalid/api',
    getHistoryDetail: id => request({ url: `/history/${id}` }),
    getScoringResult: (id, q) => request({ url: `/scoring/result/${id}/${q}` }),
    getQuestionById: id => request({ url: `/questions/${id}` }),
    evaluateAnswer: data => request({ url: '/scoring/evaluate', data }),
    usePageMotion: () => ({ motionClass: [], motionStyle: {}, visible }),
    useScrollSummary: () => ({ compact: ref(false), calibrate() {}, onSummaryScroll() {} }),
    useExamStore: () => store, useTrainingStore: () => ({ recordResult() {} }),
    useFavoritesStore: () => ({ items: [], isFavorited: () => false, load: async () => true, addItem() {}, removeItem() {} }),
    resolveAnswerMedia, scoringExplanation,
    onLoad() {}, onPageScroll() {}, onShareAppMessage: callback => shares.push(callback), onUnload: callback => unload.push(callback),
    requireLogin: () => true, showLoading() {}, hideLoading() {}, toast: message => errors.push(message), uni: {}
  })
  scope.run(() => vm.runInContext(script, context))
  const bindings = vm.runInContext(`({ loadResult, selectAnswer, retryScoring, result, transcript, displayTranscript, answerVideoUrl, answerList, activeAnswerIndex, activeExamId, activeQuestionId, retryingScoring,
    cancelRetry: typeof cancelScoringRetry === 'function' ? cancelScoringRetry : null,
    priorities: typeof reviewPriorities === 'undefined' ? null : reviewPriorities,
    loading: typeof loadingResult === 'undefined' ? null : loadingResult,
    loadError: typeof loadError === 'undefined' ? null : loadError,
    detailsOpen: typeof detailsOpen === 'undefined' ? null : detailsOpen,
    reviewRevision: typeof reviewRevision === 'undefined' ? null : reviewRevision
  })`, context)
  t.after(() => { unload.forEach(callback => callback()); scope.stop() })
  return { ...bindings, store, visible, unload, errors, requests, share: () => shares[0]() }
}

test('an older history response cannot replace a newer route or clear its loading state', async t => {
  const old = deferred(), latest = deferred()
  const f = page(t, { history: options => options.url.endsWith('exam-a') ? old.promise : latest.promise })
  const first = f.loadResult({ examId: 'exam-a' })
  const second = f.loadResult({ examId: 'exam-b' })
  old.resolve({ examId: 'exam-a', answers: [answer('q1', 20)] }); await first
  assert.equal(f.activeExamId.value, 'exam-b')
  assert.equal(f.loading?.value, true)
  latest.resolve({ examId: 'exam-b', answers: [{ ...answer('q2', 83), examId: 'exam-b' }] }); await second
  assert.equal(f.result.value.totalScore, 83)
  assert.equal(f.requests[0].signal?.aborted, true)
})

test('reopening a five-question attempt with three answers retains ordered unanswered placeholders', async t => {
  const ids = ['q3', 'q1', 'q5', 'q2', 'q4']
  const f = page(t, { history: async () => ({ examId: 'exam-a', questionIds: ids, answers: ids.slice(0, 3).map(id => answer(id, 70)) }) })
  await f.loadResult({ examId: 'exam-a', questionId: 'q5' })
  assert.deepEqual(Array.from(f.answerList.value, a => a.questionId), ids)
  assert.equal(f.answerList.value.filter(a => a.isPlaceholder).length, 2)
  assert.equal(f.activeQuestionId.value, 'q5')
  assert.equal(f.result.value.totalScore, 70)
})

test('background completion and late insertion retain the selected question and full text', async t => {
  const f = page(t, {}, [answer('q1'), answer('q2', 81)])
  f.store.questions = []
  await f.loadResult({ examId: 'exam-a', questionId: 'q2' })
  f.store.answers.unshift({ ...answer('q0', 70), questionIndex: -1 })
  f.store.answers.find(item => item.questionId === 'q1').scoringResult = { totalScore: 90, maxScore: 100 }
  await flush()
  assert.equal(f.activeQuestionId.value, 'q2')
  assert.equal(f.answerList.value[f.activeAnswerIndex.value].questionId, 'q2')
  assert.equal(f.result.value.totalScore, 81)
  assert.equal(f.displayTranscript.value, '原文 q2')
})

test('selecting another question invalidates retry success/error/finally without losing saved answers', async t => {
  const first = deferred(), second = deferred(), queue = [first, second]
  const f = page(t, { history: async () => ({ answers: [answer('q1'), answer('q2')] }), evaluate: () => queue.shift().promise })
  await f.loadResult({ examId: 'exam-a', questionId: 'q1' })
  const oldRetry = f.retryScoring()
  f.selectAnswer(1)
  const nextRetry = f.retryScoring()
  first.reject(new Error('obsolete failure')); await oldRetry
  assert.equal(f.retryingScoring.value, true)
  assert.deepEqual(f.errors, [])
  second.resolve({ totalScore: 79, maxScore: 100 }); await nextRetry
  assert.equal(f.activeQuestionId.value, 'q2')
  assert.equal(f.result.value.totalScore, 79)
  assert.equal(f.answerList.value[0].transcript, '原文 q1')
  assert.equal(f.answerList.value[0].scoringResult, null)
})

test('stopping a retry settles the wait, aborts the request, and ignores a late success', async t => {
  const pending = deferred()
  const f = page(t, { history: async () => ({ answers: [answer('q1')] }), evaluate: () => pending.promise })
  await f.loadResult({ examId: 'exam-a' })
  let settled = false
  const work = f.retryScoring().then(() => { settled = true })
  assert.equal(typeof f.cancelRetry, 'function')
  f.cancelRetry(); await flush()
  assert.equal(settled, true)
  assert.equal(f.retryingScoring.value, false)
  assert.equal(f.requests.at(-1).signal.aborted, true)
  pending.resolve({ totalScore: 95, maxScore: 100 }); await work; await flush()
  assert.equal(f.result.value, null)
  assert.equal(f.displayTranscript.value, '原文 q1')
})

test('hiding/unloading invalidates pending history and retry callbacks', async t => {
  const history = deferred()
  const f = page(t, { history: () => history.promise })
  const load = f.loadResult({ examId: 'exam-a' })
  f.visible.value = false; await flush()
  f.unload.forEach(callback => callback())
  history.resolve({ answers: [answer('q1', 97)] }); await load
  assert.equal(f.result.value, null)
  assert.deepEqual(f.errors, [])
  assert.equal(f.requests[0].signal?.aborted, true)
})

test('unscored history stays pending; genuine zero and 95+5 / suite totals retain their existing values', async t => {
  const f = page(t, { history: async () => ({ questionSummary: '已保存但未点评' }) })
  await f.loadResult({ examId: 'exam-a' })
  assert.equal(f.result.value, null)
  for (const scoringResult of [
    { totalScore: 0, maxScore: 100 },
    { totalScore: 81, maxScore: 100, contentScore: 76, contentMaxScore: 95, appearanceScore: 5, appearanceScoreMax: 5 },
    { totalScore: 29, maxScore: 35, contentScore: 26, appearanceScore: 3, appearanceScoreMax: 5, appearanceScoreScope: 'suite' }
  ]) {
    f.answerList.value = [{ ...answer('q1'), scoringResult }]
    f.selectAnswer(0)
    assert.equal(f.result.value.totalScore, scoringResult.totalScore)
    assert.equal(f.result.value.maxScore, scoringResult.maxScore)
    assert.equal(f.result.value.appearanceScore, scoringResult.appearanceScore)
  }
})

test('the actual SFC keeps full video transcript and updates collapse revision without closing it', async t => {
  const text = '  转写原文：群众反映“未能识别出有效语音”。\n' + '完整内容。'.repeat(1500) + '\n '
  const local = { ...answer('q1', 80), transcript: text, mediaType: 'video', mediaUrl: '/uploads/answer.mp4' }
  const f = page(t, {}, [local])
  await f.loadResult({ examId: 'exam-a' })
  assert.equal(f.displayTranscript.value, text)
  assert.equal(f.answerVideoUrl.value, 'https://fixture.invalid/api/uploads/answer.mp4')
  assert.ok(f.detailsOpen)
  f.detailsOpen.value = true
  const previous = f.reviewRevision.value
  f.store.answers[0].transcript += '\n异步补充末段'
  await flush()
  assert.equal(f.detailsOpen.value, true)
  assert.notDeepEqual(f.reviewRevision.value, previous)
  assert.equal(f.displayTranscript.value, text + '\n异步补充末段')
  assert.match(source, /<MotionCollapse[^>]*:revision="reviewRevision"/)
})

test('a placeholder is replaced by its real background result without switching the selected tab', async t => {
  const f = page(t, {}, [answer('q1', 73)])
  await f.loadResult({ examId: 'exam-a', questionId: 'q2' })
  assert.equal(f.answerList.value[1].isPlaceholder, true)
  f.store.answers.push({ ...answer('q2', 84), questionIndex: 1 })
  await flush()
  assert.equal(f.activeAnswerIndex.value, 1)
  assert.equal(f.activeQuestionId.value, 'q2')
  assert.equal(f.answerList.value[1].isPlaceholder, false)
  assert.equal(f.result.value.totalScore, 84)
  assert.equal(f.displayTranscript.value, '原文 q2')
})

test('stopping a local retry only detaches the page wait; its later completion does not steal another tab', async t => {
  const pending = deferred()
  const f = page(t, { retry: () => pending.promise }, [{ ...answer('q1'), processingStatus: 'failed' }, answer('q2', 88)])
  await f.loadResult({ examId: 'exam-a', questionId: 'q1' })
  let settled = false
  const retry = f.retryScoring().then(() => { settled = true })
  f.cancelRetry(); await flush()
  assert.equal(settled, true)
  assert.equal(f.store.answers[0].transcript, '原文 q1')
  f.selectAnswer(1)
  f.store.answers[0].processingStatus = 'completed'
  f.store.answers[0].scoringResult = { totalScore: 75, maxScore: 100 }
  pending.resolve(f.store.answers[0]); await retry; await flush()
  assert.equal(f.activeQuestionId.value, 'q2')
  assert.equal(f.result.value.totalScore, 88)
})

test('returning to the page refreshes the selected answer after hidden background completion', async t => {
  const f = page(t, {}, [answer('q1'), answer('q2', 83)])
  await f.loadResult({ examId: 'exam-a', questionId: 'q1' })
  f.visible.value = false
  f.store.answers[0].scoringResult = { totalScore: 77, maxScore: 100 }
  await flush()
  assert.equal(f.result.value, null)
  f.visible.value = true; await flush()
  assert.equal(f.activeAnswerIndex.value, 0)
  assert.equal(f.activeQuestionId.value, 'q1')
  assert.equal(f.result.value.totalScore, 77)
})

test('missing/partial model feedback is not padded; received priorities and full details survive hydration', async t => {
  const feedback = { source: 'model', summary: '仅有总结' }
  const f = page(t, { history: async () => ({ answers: [{ ...answer('q1', 82), questionStem: '', scoringResult: { totalScore: 82, maxScore: 100, answerImprovementSuggestion: feedback } }] }), question: async () => ({ id: 'q1', stem: '完整题干' }) })
  await f.loadResult({ examId: 'exam-a' })
  assert.equal(f.priorities.value.length, 0)
  assert.deepEqual(f.result.value.answerImprovementSuggestion, feedback)
  assert.equal(f.result.value.answerImprovementSuggestion.focusPoints, undefined)
})

test('history failure is retryable and a stale failure does not trigger fallback requests or error notices', async t => {
  const old = deferred(), latest = deferred()
  let call = 0
  const f = page(t, { history: () => ++call === 1 ? old.promise : latest.promise })
  const first = f.loadResult({ examId: 'exam-a', questionId: 'q1' })
  const second = f.loadResult({ examId: 'exam-b' })
  old.reject(new Error('obsolete')); await first
  assert.equal(f.loadError.value, '')
  assert.equal(f.requests.length, 2)
  latest.reject(new Error('temporary offline')); await second
  assert.equal(f.loadError.value, 'temporary offline')
  assert.equal(f.loading.value, false)
  latest.promise = Promise.resolve({ answers: [{ ...answer('q2', 80), examId: 'exam-b' }] })
  await f.loadResult({ examId: 'exam-b' })
  assert.equal(f.loadError.value, '')
  assert.equal(f.result.value.totalScore, 80)
})

test('a genuine retry failure retains transcript, media and timing, and retries with the same scoring contract', async t => {
  let attempts = 0
  const saved = { ...answer('q1'), mediaType: 'video', mediaUrl: '/uploads/retained.mp4', answerTiming: { actualSeconds: 155 } }
  const f = page(t, { history: async () => ({ answers: [saved] }), evaluate: async () => {
    if (++attempts === 1) throw new Error('temporary scoring failure')
    return { totalScore: 80, maxScore: 100 }
  } })
  await f.loadResult({ examId: 'exam-a' })
  await f.retryScoring()
  assert.equal(f.result.value, null)
  assert.equal(f.displayTranscript.value, '原文 q1')
  assert.equal(f.answerVideoUrl.value, 'https://fixture.invalid/api/uploads/retained.mp4')
  assert.equal(f.errors.length, 1)
  await f.retryScoring()
  assert.equal(f.result.value.totalScore, 80)
  const options = f.requests.at(-1)
  assert.equal(options.url, '/scoring/evaluate')
  assert.equal(options.method, 'POST')
  assert.equal(options.timeout, 90000)
  assert.equal(options.data.transcript, saved.transcript)
  assert.equal(options.data.answerMeta.answerTiming.actualSeconds, 155)
})

test('sharing pending work does not fabricate a zero score or change the established result route', async t => {
  const f = page(t, {}, [answer('q1')])
  await f.loadResult({ examId: 'exam-a', questionId: 'q1' })
  assert.equal(f.share().title, '面试练习复盘 · 待点评')
  assert.equal(f.share().path, '/pages/result/index?examId=exam-a&questionId=q1')
})

test('the review layout keeps actions before measured full details and emits accessible 44px controls', () => {
  assert.ok(source.indexOf('class="review-priority"') < source.indexOf('class="card review-next-action"'))
  assert.ok(source.indexOf('class="card review-next-action"') < source.indexOf('<MotionCollapse'))
  assert.match(source, /:aria-selected="index === activeAnswerIndex"/)
  assert.match(source, /:aria-expanded="detailsOpen"/)
  const style = source.match(/<style scoped>([^]*?)<\/style>/)[1]
  assert.match(style, /\.learner-result button\s*\{[^}]*min-height:\s*44px/)
  assert.ok([...style.matchAll(/font-size:\s*(\d+)px/g)].every(match => Number(match[1]) >= 14))
  assert.doesNotMatch(style, /line-clamp|max-height:\s*\d+px/)
})
