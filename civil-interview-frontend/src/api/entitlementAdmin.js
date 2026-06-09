/**
 * 这个接口文件封装管理员权益调整能力；页面不直接拼接后台 URL，避免补发、扣减和流水查询字段分散。
 *
 * @param 无；文件级模块依赖导出函数、组合式 API 或调用方传入上下文。
 * @return 导出可复用的端侧能力，具体返回值由各公共函数保持兼容。
 * @raises 不主动吞掉业务异常；请求失败、权限不足和运行时错误交由调用方或全局拦截器处理。
 */
import http from './index'

export function searchAdminUsers(params = {}) {
  return http.get('/subscription/admin/users', { params })
}

export function getAdminUserEntitlements(username) {
  return http.get(`/subscription/admin/users/${encodeURIComponent(username)}/entitlements`)
}

export function grantUserEntitlement(username, data) {
  return http.post(`/subscription/admin/users/${encodeURIComponent(username)}/grant`, data)
}

export function deductUserEntitlement(username, data) {
  return http.post(`/subscription/admin/users/${encodeURIComponent(username)}/deduct`, data)
}

export function listEntitlementAdjustments(params = {}) {
  return http.get('/subscription/admin/adjustments', { params })
}
