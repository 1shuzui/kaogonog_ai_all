import { http, USE_MOCK } from './index'
import { getMockExamStart, getMockUploadResult } from './mock/exam'
import { buildExamUploadFormData } from '@/utils/examSubmission'

export async function startExam(questionIds) {
  if (USE_MOCK) return getMockExamStart(questionIds)
  return http.post('/exam/start', { questionIds })
}

export async function uploadRecording(examId, questionId, blob) {
  if (USE_MOCK) return getMockUploadResult()
  const formData = buildExamUploadFormData({
    questionId,
    blob,
    filename: `recording_${Date.now()}.webm`,
  })
  return http.post(`/exam/${examId}/upload`, formData, {
    headers: { 'Content-Type': 'multipart/form-data' },
    timeout: 60000
  })
}

export async function completeExam(examId) {
  if (USE_MOCK) return { success: true }
  return http.post(`/exam/${examId}/complete`)
}
