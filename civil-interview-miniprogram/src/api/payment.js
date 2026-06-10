/**
 * 小程序支付接口封装，所有虚拟训练权益购买都必须走官方微信小程序虚拟支付。
 *
 * 这里只负责创建订单、确认支付和查询订单；真正的微信道具 ID、offerId、openId 和查单核验都由后端兜底。
 * 页面不能回退普通微信支付，也不能在前端自己发放权益。
 *
 * @param data: 下单、支付确认、退款统计或管理员退款处理请求体。
 * @return Promise，解析订单、虚拟支付参数、支付核验或订单列表结果。
 * @raises Error: 未登录、订单不存在、微信虚拟支付查单失败或接口异常会由 request 层抛出。
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
