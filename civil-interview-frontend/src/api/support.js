/**
 * 客服反馈接口封装，用于提交问题、管理员处理和反馈列表查询。
 *
 * 用户反馈会带题目、页面路径、地区和附件，管理员工作台再按状态处理；
 * 这里会清理空查询值，避免把 `undefined/null` 字符串传给后端造成筛选误判。
 *
 * @param params: 反馈列表筛选参数、创建反馈表单或管理员更新内容。
 * @return Promise，解析反馈列表、反馈详情、附件上传或处理结果。
 * @raises AxiosError: 未登录、非管理员处理、附件失败或反馈不存在会抛给调用页面。
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
