/**
 * PC 管理员数据看板 API 与活跃心跳封装。
 *
 * 管理员接口返回聚合后的系统、用户、付费和使用数据；心跳接口由普通登录用户静默调用，失败不打断主流程。
 */
import http from './index'

export function getDashboardOverview(params = {}) {
  return http.get('/admin/dashboard/overview', { params })
}

export function getDashboardSystem(params = {}) {
  return http.get('/admin/dashboard/system', { params })
}

export function getDashboardUsers(params = {}) {
  return http.get('/admin/dashboard/users', { params })
}

export function getDashboardUserDetail(username, params = {}) {
  return http.get(`/admin/dashboard/users/${encodeURIComponent(username)}`, { params })
}

export function reportDashboardHeartbeat(data) {
  return http.post('/admin/dashboard/heartbeat', data, {
    skipErrorHandler: true,
    timeout: 10000
  })
}
