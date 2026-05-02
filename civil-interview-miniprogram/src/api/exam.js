import { request, uploadFile } from './request'

export function startExam(questionIds = []) {
  return request({
    url: '/exam/start',
    method: 'POST',
    data: { questionIds }
  })
}

export function uploadRecording(examId, questionId, filePath) {
  return uploadFile({
    url: `/exam/${examId}/upload`,
    filePath,
    name: 'recording',
    formData: {
      questionId,
      mediaType: 'audio',
      source: 'miniapp_recording'
    },
    timeout: 60000
  })
}

export function completeExam(examId) {
  return request({
    url: `/exam/${examId}/complete`,
    method: 'POST'
  })
}
