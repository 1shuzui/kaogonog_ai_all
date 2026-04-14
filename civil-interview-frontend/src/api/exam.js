import { http, USE_MOCK } from './index'
import { getMockExamStart, getMockUploadResult } from './mock/exam'

export async function startExam(questionIds) {
  if (USE_MOCK) return getMockExamStart(questionIds)
  return http.post('/exam/start', { questionIds })
}

export async function uploadRecording(examId, blob, options = {}) {
  if (USE_MOCK) return getMockUploadResult()
  const formData = new FormData()
  formData.append('questionId', options.questionId || '')
  formData.append('mediaType', options.mediaType || blob?.type || '')
  formData.append('source', options.source || 'live_recording')
  formData.append('recording', blob, options.filename || `recording_${Date.now()}.webm`)
  return http.post(`/exam/${examId}/upload`, formData, {
    headers: { 'Content-Type': 'multipart/form-data' },
    timeout: 180000
  })
}

export async function completeExam(examId) {
  if (USE_MOCK) return { success: true }
  return http.post(`/exam/${examId}/complete`)
}
