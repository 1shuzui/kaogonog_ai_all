import { http, USE_MOCK } from './index'
import { getMockTranscript, getMockScoringResult } from './mock/exam'

export async function transcribeAudio(audioBlob) {
  if (USE_MOCK) return getMockTranscript()
  const blobType = audioBlob?.type || ''
  const extension = blobType.includes('wav')
    ? 'wav'
    : blobType.includes('mpeg') || blobType.includes('mp3')
      ? 'mp3'
      : blobType.includes('mp4') || blobType.includes('m4a')
        ? 'm4a'
        : 'webm'
  const formData = new FormData()
  formData.append('audio', audioBlob, `recording_${Date.now()}.${extension}`)
  return http.post('/scoring/transcribe', formData, {
    headers: { 'Content-Type': 'multipart/form-data' },
    timeout: 60000
  })
}

export async function evaluateAnswer(data) {
  if (USE_MOCK) return getMockScoringResult(data.questionId)
  return http.post('/scoring/evaluate', data)
}

export async function getScoringResult(examId, questionId) {
  if (USE_MOCK) return getMockScoringResult(questionId)
  return http.get(`/scoring/result/${examId}/${questionId}`)
}
