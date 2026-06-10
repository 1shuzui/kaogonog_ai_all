/**
 * 试用权益接口封装，保证试用题、试用状态和完成标记都经过账号边界。
 *
 * 小程序首页可以先浏览，但试用题必须登录后使用，因为完成状态、防重复试用和权益边界都依赖账号。
 *
 * @param config: 可选请求配置，常用于静默刷新试用状态。
 * @return Promise，解析试用状态、试用题或完成标记结果。
 * @raises Error: 未登录、试用已完成、题目不可用或接口失败会由 request 层抛出。
 */
import { request } from './request'

export function getTrialStatus(config = {}) {
  return request({
    url: '/trial/status',
    ...config
  })
}

export function getTrialQuestion() {
  return request({
    url: '/trial/question'
  })
}

export function completeTrial() {
  return request({
    url: '/trial/complete',
    method: 'POST',
    skipErrorHandler: true
  })
}
