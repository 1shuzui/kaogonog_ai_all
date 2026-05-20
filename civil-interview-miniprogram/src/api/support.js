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
