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
