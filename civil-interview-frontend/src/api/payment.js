/**
 * 支付接口封装，保留 PC 端订单与退款查询能力；微信虚拟支付口径由后端和小程序侧兜底。
 *
 * 虚拟训练权益的真实支付必须走微信小程序官方虚拟支付；PC 端保留订单中心、退款和管理员核查入口，
 * 但不能新增普通微信支付或模拟支付回退。
 *
 * @param data: 下单、支付确认、退款统计或管理员退款处理请求体。
 * @return Promise，解析订单、支付核验、退款统计或退款处理结果。
 * @raises AxiosError: 未登录、非管理员、订单不存在、微信查单失败或接口失败会抛给调用页面。
 */
import http from './index'

export function createPaymentOrder(data) {
  return http.post('/payment/orders', data)
}

export function getMyPaymentOrders() {
  return http.get('/payment/orders/me')
}

export function getPaymentOrder(orderNo) {
  return http.get(`/payment/orders/${encodeURIComponent(orderNo)}`)
}

export function getRefundBalanceStats(data = {}) {
  return http.post('/payment/admin/refund-stats', data)
}

export function applyRefund(data) {
  return http.post('/payment/admin/refund', data)
}

export function verifyVirtualPaymentOrder(orderNo, data = {}) {
  return http.post(`/payment/orders/${encodeURIComponent(orderNo)}/virtual/verify`, data)
}

export function confirmVirtualPaymentOrder(orderNo, data = {}) {
  return http.post(`/payment/orders/${encodeURIComponent(orderNo)}/virtual/confirm`, data)
}
