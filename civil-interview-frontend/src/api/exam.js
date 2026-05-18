import { http } from './index'
import { buildExamUploadFormData } from '@/utils/examSubmission'

export async function startExam(questionIds) {
  return http.post('/exam/start', { questionIds })
}

export async function uploadRecording(examId, questionId, blob) {
  const formData = buildExamUploadFormData({
    questionId,
    blob,
    filename: `recording_${Date.now()}.webm`
  })
  return http.post(`/exam/${examId}/upload`, formData, {
    headers: { 'Content-Type': 'multipart/form-data' },
    timeout: 60000
  })
}

export async function completeExam(examId) {
  return http.post(`/exam/${examId}/complete`)
}
