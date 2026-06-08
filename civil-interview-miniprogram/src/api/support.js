/**
 * 这个接口文件负责用户反馈和客服处理接口封装；页面只调用这里的方法，避免到处拼 URL 和重复处理错误。
 *
 * @param 无；文件级模块依赖导出函数、组合式 API 或调用方传入上下文。
 * @return 导出可复用的端侧能力，具体返回值由各公共函数保持兼容。
 * @raises 不主动吞掉业务异常；请求失败、权限不足和运行时错误交由调用方或全局拦截器处理。
 */
import { API_BASE, request, uploadFile } from './request'

function resolveSupportAttachmentUrl(url = '') {
  const value = String(url || '')
  if (!value || /^https?:\/\//i.test(value)) return value
  if (value.startsWith('/api/')) {
    return `${API_BASE.replace(/\/api\/?$/, '')}${value}`
  }
  return `${API_BASE.replace(/\/+$/, '')}${value.startsWith('/') ? value : `/${value}`}`
}

export function normalizeSupportAttachment(item = {}) {
  return {
    ...item,
    url: resolveSupportAttachmentUrl(item.url)
  }
}

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

export function getSupportFeedback(params = {}, config = {}) {
  return request({
    url: '/support/feedback',
    data: cleanSupportQuery(params),
    skipErrorHandler: true,
    ...config
  })
}

export function createSupportFeedback(data, config = {}) {
  return request({
    url: '/support/feedback',
    method: 'POST',
    data,
    skipErrorHandler: true,
    ...config
  })
}

export async function uploadSupportFeedbackImage(filePath, config = {}) {
  const response = await uploadFile({
    url: '/support/feedback/attachments',
    filePath,
    name: 'file',
    skipErrorHandler: true,
    ...config
  })
  return normalizeSupportAttachment(response)
}

export function updateSupportFeedback(feedbackId, data, config = {}) {
  return request({
    url: `/support/feedback/${feedbackId}`,
    method: 'PATCH',
    data,
    skipErrorHandler: true,
    ...config
  })
}

export function deleteSupportFeedback(feedbackId, config = {}) {
  return request({
    url: `/support/feedback/${feedbackId}`,
    method: 'DELETE',
    skipErrorHandler: true,
    ...config
  })
}
