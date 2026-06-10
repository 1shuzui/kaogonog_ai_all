/**
 * PC 管理员权益 API 封装，集中调用用户搜索、权益详情、人工补发、扣减和调整流水接口。
 *
 * 这些接口只给管理员工作台使用，普通用户页面不应引用。人工权益调整与微信支付订单分离，前端必须传原因和备注，
 * 让后端写入审计流水并刷新用户权益快照。
 *
 * @param 各函数接收用户名、分页筛选、补发请求或扣减请求。
 * @return Promise，解析后端返回的用户权益详情、调整结果或流水列表。
 * @raises AxiosError: 未登录、非管理员、参数越界或用户/权益不存在时由请求层抛出。
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
