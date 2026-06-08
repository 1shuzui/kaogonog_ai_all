/**
 * 这个接口文件负责订单、虚拟支付和退款接口封装；页面只调用这里的方法，避免到处拼 URL 和重复处理错误。
 *
 * @param 无；文件级模块依赖导出函数、组合式 API 或调用方传入上下文。
 * @return 导出可复用的端侧能力，具体返回值由各公共函数保持兼容。
 * @raises 不主动吞掉业务异常；请求失败、权限不足和运行时错误交由调用方或全局拦截器处理。
 */
import { request } from './request'

export function createPaymentOrder(data) {
  return request({
    url: '/payment/orders',
    method: 'POST',
    data
  })
}

export function getPaymentOrder(orderNo) {
  return request({
    url: `/payment/orders/${encodeURIComponent(orderNo)}`
  })
}

export function verifyVirtualPaymentOrder(orderNo, data = {}) {
  return request({
    url: `/payment/orders/${encodeURIComponent(orderNo)}/virtual/verify`,
    method: 'POST',
    data
  })
}

export function confirmVirtualPaymentOrder(orderNo, data = {}) {
  return request({
    url: `/payment/orders/${encodeURIComponent(orderNo)}/virtual/confirm`,
    method: 'POST',
    data
  })
}

export function getMyPaymentOrders() {
  return request({
    url: '/payment/orders/me'
  })
}

export function getRefundBalanceStats(data = {}) {
  return request({
    url: '/payment/admin/refund-stats',
    method: 'POST',
    data
  })
}

export function applyRefund(data) {
  return request({
    url: '/payment/admin/refund',
    method: 'POST',
    data
  })
}
