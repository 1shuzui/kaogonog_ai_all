import { http } from './index'

export async function getSubscriptionStatus(config = {}) {
  return http.get('/subscription/me', config)
}

export async function checkSubscriptionAccess(mode = 'practice', config = {}) {
  return http.get('/subscription/check-access', { params: { mode }, ...config })
}

export async function switchSubscription(subscriptionId, config = {}) {
  return http.post('/subscription/switch', { subscriptionId }, config)
}
