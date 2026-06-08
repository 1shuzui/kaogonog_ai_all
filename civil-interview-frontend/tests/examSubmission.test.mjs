/**
 * 这个前端测试文件守住 `examSubmission.test` 的回归行为；它让提交表单、页面联动这类细节不会悄悄退化。
 *
 * @param 无；测试数据在用例内部构造，避免依赖浏览器录音环境。
 * @return 通过断言验证上传表单和空录音判断仍符合业务边界。
 * @raises AssertionError 当提交字段或空录音规则被改坏时由测试框架抛出。
 */
import test from 'node:test'
import assert from 'node:assert/strict'

import {
  buildExamUploadFormData,
  hasRecordingContent,
} from '../src/utils/examSubmission.js'

test('buildExamUploadFormData includes questionId for upload requests', (t) => {
  const blob = new Blob(['answer'], { type: 'audio/webm' })
  const formData = buildExamUploadFormData({
    questionId: 'question_001',
    blob,
    filename: 'answer.webm',
  })

  assert.equal(formData.get('questionId'), 'question_001')
  assert.ok(formData.get('recording') instanceof Blob)
})

test('hasRecordingContent treats empty blobs as empty answers', (t) => {
  assert.equal(hasRecordingContent(null), false)
  assert.equal(hasRecordingContent(undefined), false)
  assert.equal(hasRecordingContent(new Blob([], { type: 'audio/webm' })), false)
  assert.equal(hasRecordingContent(new Blob(['voice'], { type: 'audio/webm' })), true)
})
