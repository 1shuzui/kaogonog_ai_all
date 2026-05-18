import { request, uploadFile } from './request'

export function startExam(questionIds = []) {
  return request({
    url: '/exam/start',
    method: 'POST',
    data: { questionIds }
  })
}

export function uploadRecording(examId, questionId, filePath, options = {}) {
  const mediaType = options.mediaType || 'audio'
  return uploadFile({
    url: `/exam/${examId}/upload`,
    filePath,
    name: 'recording',
    formData: {
      questionId,
      mediaType,
      source: options.source || `miniapp_${mediaType}_recording`
    },
    timeout: mediaType === 'video' ? 120000 : 60000
  })
}

export function completeExam(examId) {
  return request({
    url: `/exam/${examId}/complete`,
    method: 'POST'
  })
}
