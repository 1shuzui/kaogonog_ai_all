import { http } from './index'

export async function getAsrStatus(config = {}) {
  return http.get('/scoring/asr-status', config)
}

export async function transcribeAudio(audioBlob) {
  const formData = new FormData()
  formData.append('audio', audioBlob, `answer_${Date.now()}${getAudioExtension(audioBlob?.type)}`)
  return http.post('/scoring/transcribe', formData, {
    headers: { 'Content-Type': 'multipart/form-data' },
    timeout: 60000
  })
}

function getAudioExtension(mimeType = '') {
  const normalized = String(mimeType || '').split(';')[0].toLowerCase()
  if (normalized.includes('mp4')) return '.m4a'
  if (normalized.includes('mpeg') || normalized.includes('mp3')) return '.mp3'
  if (normalized.includes('ogg')) return '.ogg'
  if (normalized.includes('wav')) return '.wav'
  return '.webm'
}

export async function evaluateAnswer(data) {
  return http.post('/scoring/evaluate', data)
}

export async function getScoringResult(examId, questionId) {
  return http.get(`/scoring/result/${examId}/${questionId}`)
}
