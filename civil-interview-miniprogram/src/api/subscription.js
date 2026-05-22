import { request } from './request'

export function getSubscriptionStatus(config = {}) {
  return request({
    url: '/subscription/me',
    ...config
  })
}

export function checkSubscriptionAccess(mode = 'practice', config = {}) {
  return request({
    url: '/subscription/check-access',
    data: { mode },
    ...config
  })
}

export function switchSubscription(subscriptionId, config = {}) {
  return request({
    url: '/subscription/switch',
    method: 'POST',
    data: { subscriptionId },
    ...config
  })
}
