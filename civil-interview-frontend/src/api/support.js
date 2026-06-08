/**
 * 这个接口文件负责用户反馈和客服处理接口封装；页面只调用这里的方法，避免到处拼 URL 和重复处理错误。
 *
 * @param 无；文件级模块依赖导出函数、组合式 API 或调用方传入上下文。
 * @return 导出可复用的端侧能力，具体返回值由各公共函数保持兼容。
 * @raises 不主动吞掉业务异常；请求失败、权限不足和运行时错误交由调用方或全局拦截器处理。
 */
import { http } from './index'

function cleanSupportQuery(params = {}) {
  return Object.fromEntries(
    Object.entries(params).filter(([, value]) => (
      value !== undefined &&
      value !== null &&
      String(value).trim() !== '' &&
      String(value).trim() !== 'undefined' &&
      String(value).trim() !== 'null'
    ))
  )
}

export function getSupportFeedback(params = {}) {
  return http.get('/support/feedback', {
    params: cleanSupportQuery(params),
    skipErrorHandler: true
  })
}

export function createSupportFeedback(data) {
  return http.post('/support/feedback', data, {
    skipErrorHandler: true
  })
}

export function uploadSupportFeedbackImage(file) {
  const formData = new FormData()
  formData.append('file', file)
  return http.post('/support/feedback/attachments', formData, {
    skipErrorHandler: true
  })
}

export function updateSupportFeedback(feedbackId, data) {
  return http.patch(`/support/feedback/${feedbackId}`, data, {
    skipErrorHandler: true
  })
}

export function deleteSupportFeedback(feedbackId) {
  return http.delete(`/support/feedback/${feedbackId}`, {
    skipErrorHandler: true
  })
}
