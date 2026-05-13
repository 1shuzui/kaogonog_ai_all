import { request } from './request'

export function getSupportFeedback(params = {}, config = {}) {
  return request({
    url: '/support/feedback',
    data: params,
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
