/**
 * PC 管理员邀请码 API 封装。
 *
 * 邀请码只在注册和后台报表使用，普通用户不展示归因信息；管理员接口统一走后端鉴权。
 */
import http from './index'

export function listInvitePartners() {
  return http.get('/invite/admin/partners')
}

export function createInvitePartner(data) {
  return http.post('/invite/admin/partners', data)
}

export function updateInvitePartner(partnerId, data) {
  return http.put(`/invite/admin/partners/${partnerId}`, data)
}

export function deleteInvitePartner(partnerId) {
  return http.delete(`/invite/admin/partners/${partnerId}`)
}

export function listInviteCodes(params = {}) {
  return http.get('/invite/admin/codes', { params })
}

export function createInviteCode(data) {
  return http.post('/invite/admin/codes', data)
}

export function updateInviteCode(codeId, data) {
  return http.put(`/invite/admin/codes/${codeId}`, data)
}

export function deleteInviteCode(codeId) {
  return http.delete(`/invite/admin/codes/${codeId}`)
}

export function correctInviteAttribution(username, data) {
  return http.post(`/invite/admin/users/${encodeURIComponent(username)}/correction`, data)
}

export function getInviteReport(data) {
  return http.post('/invite/admin/report', data)
}

export function exportInviteReport(data) {
  return http.post('/invite/admin/report.csv', data, {
    responseType: 'blob'
  })
}
