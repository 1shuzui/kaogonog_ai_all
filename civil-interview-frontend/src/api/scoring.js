import { http, USE_MOCK } from './index'
import { getMockTranscript, getMockScoringResult } from './mock/exam'

export async function transcribeAudio(audioBlob, options = {}) {
  if (USE_MOCK) return getMockTranscript()
  const formData = new FormData()
  formData.append('audio', audioBlob, options.filename || `answer_${Date.now()}.webm`)
  return http.post('/scoring/transcribe', formData, {
    headers: { 'Content-Type': 'multipart/form-data' },
    timeout: 180000
  })
}

export async function evaluateAnswer(data) {
  if (USE_MOCK) return getMockScoringResult(data.questionId)
  return http.post('/scoring/evaluate', data, { timeout: 180000 })
}

export async function getScoringResult(examId, questionId) {
  if (USE_MOCK) return getMockScoringResult(questionId)
  return http.get(`/scoring/result/${examId}/${questionId}`)
}
