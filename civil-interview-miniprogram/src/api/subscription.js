/**
 * 权益订阅接口封装，统一读取套餐、余额、订单和支付状态，避免端侧权益口径分裂。
 *
 * 剩余分钟、每日限额、试用状态和管理员人工调整都以后端快照为准；
 * 小程序只展示和刷新，不能因为本地计时或缓存自行改余额。
 *
 * @param mode: 权益校验场景，例如 practice、exam 或 trial。
 * @param subscriptionId: 用户主动切换使用的权益 ID。
 * @return Promise，解析当前权益、访问校验或权益切换结果。
 * @raises Error: 未登录、权益不足、权益不存在或接口失败会由 request 层抛出。
 */
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
