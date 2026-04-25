export function hasRecordingContent(blob) {
  return blob instanceof Blob && blob.size > 0
}

export function buildExamUploadFormData({ questionId, blob, filename }) {
  const formData = new FormData()
  formData.append('questionId', String(questionId || ''))
  formData.append('recording', blob, filename || `recording_${Date.now()}.webm`)
  return formData
}
