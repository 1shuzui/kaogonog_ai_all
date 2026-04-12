import { http, USE_MOCK } from './index'
import { getMockExamStart, getMockUploadResult } from './mock/exam'

export async function startExam(questionIds) {
  if (USE_MOCK) return getMockExamStart(questionIds)
  return http.post('/exam/start', { questionIds })
}

export async function uploadRecording(examId, blob) {
  if (USE_MOCK) return getMockUploadResult()
  const formData = new FormData()
  formData.append('recording', blob, `recording_${Date.now()}.webm`)
  return http.post(`/exam/${examId}/upload`, formData, {
    headers: { 'Content-Type': 'multipart/form-data' },
    timeout: 60000
  })
}

export async function completeExam(examId) {
  if (USE_MOCK) return { success: true }
  return http.post(`/exam/${examId}/complete`)
}
