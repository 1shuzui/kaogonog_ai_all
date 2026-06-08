/**
 * 这个接口文件负责转写、评分和评分状态接口封装；页面只调用这里的方法，避免到处拼 URL 和重复处理错误。
 *
 * @param 无；文件级模块依赖导出函数、组合式 API 或调用方传入上下文。
 * @return 导出可复用的端侧能力，具体返回值由各公共函数保持兼容。
 * @raises 不主动吞掉业务异常；请求失败、权限不足和运行时错误交由调用方或全局拦截器处理。
 */
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
