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
