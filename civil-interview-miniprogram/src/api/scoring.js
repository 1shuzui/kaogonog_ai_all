import { request, uploadFile } from './request'

export function transcribeAudio(filePath) {
  return uploadFile({
    url: '/scoring/transcribe',
    filePath,
    name: 'audio',
    timeout: 60000
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
