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

export function compensateSubscription(data) {
  return request({
    url: '/payment/admin/compensate',
    method: 'POST',
    data
  })
}
