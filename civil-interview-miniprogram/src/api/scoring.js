/**
 * 这个接口文件负责转写、评分和评分状态接口封装；页面只调用这里的方法，避免到处拼 URL 和重复处理错误。
 *
 * @param 无；文件级模块依赖导出函数、组合式 API 或调用方传入上下文。
 * @return 导出可复用的端侧能力，具体返回值由各公共函数保持兼容。
 * @raises 不主动吞掉业务异常；请求失败、权限不足和运行时错误交由调用方或全局拦截器处理。
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
  return uploadFile({
    url: '/scoring/transcribe',
    filePath,
    name: 'audio',
    timeout: mediaType === 'video' ? 120000 : 60000,
    formData: {
      mediaType
    }
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
