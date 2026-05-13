import { request, uploadFile } from './request'

export function getAsrStatus(config = {}) {
  return request({
    url: '/scoring/asr-status',
    ...config
  })
}

export function transcribeAudio(filePath, options = {}) {
  const mediaType = options.mediaType || 'audio'
  return uploadFile({
    url: '/scoring/transcribe',
    filePath,
    name: 'audio',
    timeout: mediaType === 'video' ? 120000 : 60000,
    formData: {
      mediaType
    }
  })
}

export function evaluateAnswer(data) {
  return request({
    url: '/scoring/evaluate',
    method: 'POST',
    data
  })
}

export function getScoringResult(examId, questionId) {
  return request({
    url: `/scoring/result/${examId}/${questionId}`
  })
}
