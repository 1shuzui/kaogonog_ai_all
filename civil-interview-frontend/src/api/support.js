import { http } from './index'

export function getSupportFeedback(params = {}) {
  return http.get('/support/feedback', {
    params,
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
