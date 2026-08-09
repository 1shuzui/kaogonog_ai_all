/**
 * 评分接口封装，承接文字、音频和视频评分请求，让页面只处理上传状态和结果展示。
 *
 * 录音转写可能走 FunASR/VAD，评分可能走 LLM 和题库采分点；页面不要把占位文字稿当作可靠答案，
 * 也不要在评分前显示题目分数或扣分细节。
 *
 * @param audioBlob: PC 端录制得到的音频 Blob。
 * @param data: 评分请求所需的题目 ID、文字稿、考试 ID 或媒体上下文。
 * @return Promise，解析 ASR 状态、文字稿、评分结果或媒体上传结果。
 * @raises AxiosError: ASR 未配置、上传失败、题目不存在或评分失败会抛给考场/结果页处理。
 */
import { http } from './index'

export async function getAsrStatus(config = {}) {
  return http.get('/scoring/asr-status', config)
}

export async function transcribeAudio(audioBlob, options = {}) {
  const formData = new FormData()
  formData.append('audio', audioBlob, `answer_${Date.now()}${getAudioExtension(audioBlob?.type)}`)
  if (options.questionId) {
    formData.append('questionId', options.questionId)
  }
  if (options.examId) {
    formData.append('examId', options.examId)
  }
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
