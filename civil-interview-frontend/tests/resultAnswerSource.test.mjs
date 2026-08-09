/**
 * 结果页历史答案来源回归测试，防止路由指定的历史考试被当前 store 状态覆盖。
 */
import test from 'node:test'
import assert from 'node:assert/strict'

import { canUseLocalAnswers } from '../src/utils/resultAnswerSource.js'

test('result page rejects local answers from another exam', () => {
  assert.equal(canUseLocalAnswers('history-exam', 'current-exam', [{ examId: 'current-exam' }]), false)
  assert.equal(canUseLocalAnswers('history-exam', 'history-exam', [{ examId: 'history-exam' }]), true)
  assert.equal(canUseLocalAnswers('', 'current-exam', [{ examId: 'current-exam' }]), true)
  assert.equal(canUseLocalAnswers('history-exam', '', [{ questionId: 'q1' }]), false)
  assert.equal(canUseLocalAnswers('history-exam', 'history-exam', []), false)
})
