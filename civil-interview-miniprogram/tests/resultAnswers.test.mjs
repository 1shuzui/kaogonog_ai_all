import test from 'node:test'
import assert from 'node:assert/strict'
import { buildDisplayAnswers, formatAnswerScore, normalizeDisplayResult, normalizeAnswerTiming, resolveNoContentReason } from '../src/utils/resultAnswers.mjs'

test('result answer mapping preserves source data and inserts placeholders in the actual question order', () => {
  const input = [{ questionId: 'q1', transcript: '完整原文', scoringResult: { totalScore: 0, maxScore: 32 } }]
  const original = structuredClone(input)
  const display = buildDisplayAnswers(input, ['q2', 'q1'], 'e')
  assert.deepEqual(display.map(answer => answer.questionId), ['q2', 'q1'])
  assert.equal(display[0].isPlaceholder, true)
  assert.equal(formatAnswerScore(display[0]), '未作答')
  assert.equal(formatAnswerScore({ questionId: 'pending', scoringResult: null }), '待点评')
  assert.equal(formatAnswerScore(display[1]), '0/32分')
  assert.deepEqual(input, original)
})

test('result normalization preserves received feedback and suite appearance fields without adding advice', () => {
  const feedback = { source: 'model', summary: '已收到的总结' }
  const result = normalizeDisplayResult({ totalScore: 29, maxScore: 35, contentScore: 26, appearanceScore: 3,
    appearanceScoreMax: 5, appearanceScoreScope: 'suite', answerImprovementSuggestion: feedback })
  assert.equal(result.totalScore, 29)
  assert.equal(result.maxScore, 35)
  assert.equal(result.appearanceScoreScope, 'suite')
  assert.equal(result.answerImprovementSuggestion, feedback)
  assert.equal(normalizeDisplayResult({ totalScore: 0 }).answerImprovementSuggestion, null)
})

test('result timing and no-content reasons remain separate from valid answer text', () => {
  assert.deepEqual(normalizeAnswerTiming({ usageSeconds: 65, standardSeconds: 60 }), { actualSeconds: 65, standardSeconds: 60, overtimeSeconds: 5 })
  assert.equal(resolveNoContentReason('原稿中提到未识别到有效语音，但实际有完整答题内容。'), null)
  assert.equal(resolveNoContentReason('', { scoringMode: 'empty_zero', skipReason: 'user_confirmed_skip' }).title, '用户确认跳过')
})
