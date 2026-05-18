import { request, uploadFile } from './request'

export function startExam(questionIds = []) {
  return request({
    url: '/exam/start',
    method: 'POST',
    data: { questionIds }
  })
}

export function getFullMockSuites(params = {}) {
  return request({
    url: '/exam/full-mock/suites',
    data: params
  })
}

export function getFullMockSuite(id) {
  return request({
    url: `/exam/full-mock/suites/${encodeURIComponent(id)}`
  })
}

export function startFullMockSuite(id) {
  return request({
    url: `/exam/full-mock/suites/${encodeURIComponent(id)}/start`,
    method: 'POST'
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
