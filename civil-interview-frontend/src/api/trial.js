/**
 * 试用权益接口封装，保证试用题、试用状态和完成标记都经过账号边界。
 *
 * 审核要求用户可先浏览功能，但试用题必须登录后使用，因为完成状态和防重复试用都依赖账号。
 *
 * @param config: 可选请求配置，常用于静默刷新试用状态。
 * @return Promise，解析试用状态、试用题或完成标记结果。
 * @raises AxiosError: 未登录、试用已完成、题目不可用或接口失败会抛给调用页面。
 */
import { http } from './index'

export async function getTrialStatus(config = {}) {
  return http.get('/trial/status', config)
}

export async function getTrialQuestion() {
  return http.get('/trial/question')
}

export async function completeTrial() {
  return http.post('/trial/complete')
}
