/**
 * 评分接口封装，承接文字、音频和视频评分请求，让页面只处理上传状态和结果展示。
 *
 * 小程序录音可能先经 FunASR/VAD 转写，再进入 LLM 评分；页面不要把占位文字稿当作可靠答案，
 * 也不要在练习或考试阶段提前显示题目分数。
 *
 * @param filePath: 小程序录音或录像的本地临时文件路径。
 * @param options: 上传媒体类型、文件名、题目上下文或评分请求配置。
 * @return Promise，解析 ASR 状态、文字稿、评分结果或媒体上传结果。
 * @raises Error: 麦克风/文件异常、ASR 未配置、上传失败、题目不存在或评分失败会由 request 层抛出。
 */
import { request, uploadFile } from './request'

export function getAsrStatus(config = {}) {
  return request({
    url: '/scoring/asr-status',
    ...config
  })
}

export function transcribeAudio(filePath, options = {}) {
  const mediaType = options.mediaType || 'audio'
  const formData = { mediaType }
  if (options.questionId) {
    formData.questionId = options.questionId
  }
  if (options.examId) {
    formData.examId = options.examId
  }
  return uploadFile({
    url: '/scoring/transcribe',
    filePath,
    name: 'audio',
    timeout: mediaType === 'video' ? 120000 : 60000,
    formData
  })
}

export function evaluateAnswer(data) {
  return request({
    url: '/scoring/evaluate',
    method: 'POST',
    data,
    timeout: 90000
  })
}

export function getScoringResult(examId, questionId) {
  return request({
    url: `/scoring/result/${examId}/${questionId}`
  })
}
