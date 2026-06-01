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
