/**
 * 客服反馈接口封装，用于提交问题、管理员处理和反馈列表查询。
 *
 * 反馈需要带上页面路径、题目、地区和附件，管理员端才能定位问题来源；
 * 附件 URL 在这里补齐后端基地址，避免页面拿到相对路径后无法预览。
 *
 * @param params: 反馈列表筛选、创建反馈表单或管理员更新内容。
 * @return Promise，解析反馈列表、附件上传、创建反馈或处理结果。
 * @raises Error: 未登录、附件上传失败、非管理员处理或接口异常会由 request 层抛出。
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
