/**
 * 权益订阅接口封装，统一读取套餐、余额、订单和支付状态，避免端侧权益口径分裂。
 *
 * 真实剩余时长以后端为准，端侧只展示快照；管理员补发、退款扣减和微信虚拟支付到账都会刷新这条链路。
 * 练习页不能自行修改余额，只能上报用量后重新读取状态。
 *
 * @param mode: 权益校验场景，例如 practice、exam 或 trial。
 * @param subscriptionId: 用户主动切换使用的权益 ID。
 * @return Promise，解析套餐列表、当前权益、访问校验或权益切换结果。
 * @raises AxiosError: 未登录、权益不足、权益不存在或接口失败会抛给调用页面处理。
 */
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
