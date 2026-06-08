/**
 * 这个接口文件负责订单、虚拟支付和退款接口封装；页面只调用这里的方法，避免到处拼 URL 和重复处理错误。
 *
 * @param 无；文件级模块依赖导出函数、组合式 API 或调用方传入上下文。
 * @return 导出可复用的端侧能力，具体返回值由各公共函数保持兼容。
 * @raises 不主动吞掉业务异常；请求失败、权限不足和运行时错误交由调用方或全局拦截器处理。
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
