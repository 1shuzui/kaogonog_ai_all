import test from 'node:test'
import assert from 'node:assert/strict'
import { readReviewSuggestion, getReviewPriorities, getReviewTranscript } from '../src/utils/resultReview.mjs'

test('missing suggestion data never creates a diagnosis, sample answer, or priority', () => {
  assert.equal(readReviewSuggestion(null), null)
  assert.equal(readReviewSuggestion({}), null)
  assert.deepEqual(getReviewPriorities(null), [])
  const suggestion = readReviewSuggestion({ source: 'model', summary: '已有评语' })
  assert.equal(suggestion.summary, '已有评语')
  assert.deepEqual(suggestion.focusPoints, [])
  assert.equal(suggestion.sampleAnswer, '')
  assert.deepEqual(getReviewPriorities(suggestion), [])
})

test('priorities preserve model wording and order, deduplicate, and show at most three', () => {
  const raw = { source: 'model', focusPoints: [
    { title: '明确对象', hint: '先说明服务对象。' },
    { title: '明确对象', hint: '先说明服务对象。' },
    { title: '补充步骤', hint: '补充核实与反馈步骤。' },
    { title: '交代责任', hint: '交代责任分工。' },
    { title: '说明时限', hint: '说明处理时限。' }
  ] }
  const snapshot = JSON.stringify(raw)
  const suggestion = readReviewSuggestion(raw)
  assert.equal(suggestion.focusPoints.length, 5, 'full details are not truncated')
  assert.deepEqual(getReviewPriorities(suggestion).map(item => [item.title, item.text]), [
    ['明确对象', '先说明服务对象。'], ['补充步骤', '补充核实与反馈步骤。'], ['交代责任', '交代责任分工。']
  ])
  assert.equal(JSON.stringify(raw), snapshot)
})

test('generic fallback and unattributed suggestions are not presented as personal priorities', () => {
  for (const source of ['fallback', '', 'unknown']) {
    assert.deepEqual(getReviewPriorities(readReviewSuggestion({ source, focusPoints: ['通用措施'] })), [])
  }
})

test('existing expression and rewrite suggestions can supply actions without invented advice', () => {
  const suggestion = readReviewSuggestion({ source: 'model', expression_upgrades: [{ before: '去处理', after: '先核实，再协调' }], rewrite_opening: '先说明工作目标。' })
  assert.deepEqual(getReviewPriorities(suggestion).map(item => item.text), ['先核实，再协调', '先说明工作目标。'])
  assert.equal(suggestion.expressionUpgrades[0].before, '去处理')
  assert.equal(suggestion.teacherComment, '')
})

test('invalid fields are ignored instead of rendered as object strings', () => {
  const suggestion = readReviewSuggestion({ source: 'model', summary: '评语', focusPoints: [null, {}, 42, { title: {}, hint: [] }], diagnosisItems: [{ text: 'bad' }] })
  assert.deepEqual(getReviewPriorities(suggestion), [])
  assert.deepEqual(suggestion.diagnosisItems, [])
})

test('audio/video actual text, line breaks and quoted ASR phrases remain complete', () => {
  const actual = '  第一段\n群众反映“未能识别出有效语音”，我会核查服务问题。\n' + '完整作答。'.repeat(1500) + '\n  '
  assert.equal(getReviewTranscript(actual), actual)
  for (const placeholder of ['', '  ', '未作答', '未能识别出有效语音', '无法生成可靠文字稿']) {
    assert.equal(getReviewTranscript(placeholder), '')
  }
})
