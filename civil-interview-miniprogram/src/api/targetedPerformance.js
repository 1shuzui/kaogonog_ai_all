import { request } from './request'
import { validateReport } from '../utils/targetedPerformance.mjs'

const post = (url, data, options) => request({ url, method: 'POST', data, timeout: 30000, skipErrorHandler: true, ...options })
export async function getPerformance(data, options = {}) {
  return validateReport(await post('/targeted/performance', data, options))
}
export async function getPerformanceAnswers(data, options = {}) {
  const response = await post('/targeted/performance/answers', data, options)
  validateReport(response?.report)
  if (!Array.isArray(response.list) || !Number.isInteger(response.total)) throw new Error('答题记录读取失败，请重试')
  return response
}
export async function selectTargetedPractice(data, options = {}) {
  const response = await post('/targeted/practice-selections', data, options)
  if (!Array.isArray(response?.questionIds) || response.actualCount !== response.questionIds.length
    || new Set(response.questionIds).size !== response.questionIds.length || !response.targetedContext) throw new Error('选题结果不完整，请重试')
  return response
}
