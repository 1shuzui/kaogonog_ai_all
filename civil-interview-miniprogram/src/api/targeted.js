/**
 * 定向备面接口封装，集中处理分类树、重点分析、专项生成和管理员发布内容。
 *
 * 定向页允许未登录浏览分类树，但分析、生成和开通动作必须登录；
 * 分类层级由后端 levelLabels 驱动，法检等特殊体系不能把自己的“岗位方向”标题影响到其他体系。
 *
 * @param payload: 考试体系、地区/来源、方向、时间模式和题量等筛选字段。
 * @return Promise，解析分类树、重点分析、生成题目或管理员发布配置。
 * @raises Error: 未登录、非管理员、无题库数据或接口失败会由 request 层抛出。
 */
import { request } from './request'

export const FOCUS_TIMEOUT_MS = 30000
export const FOCUS_SLOW_MS = 10000

function normalizeFocusAnalysis(response = {}) {
  if (typeof response === 'string') {
    try { response = JSON.parse(response) } catch {
      throw Object.assign(new Error('分析结果格式异常，请重试'), { code: 'PARSE_ERROR' })
    }
  }
  if (response?.success === false) {
    throw Object.assign(new Error(response.message || response.detail || '本次分析未完成，请重试'), { code: 'BUSINESS_ERROR' })
  }
  if (!response || typeof response !== 'object' || Array.isArray(response)
    || response.questionCount == null || response.questionCount === ''
    || !Number.isFinite(Number(response.questionCount)) || Number(response.questionCount) < 0
    || ['coreFocus', 'focusAreas', 'highFreqTypes', 'hotTopics', 'strategy'].some(key => response[key] != null && !Array.isArray(response[key]))
    || ['coreFocus', 'focusAreas', 'highFreqTypes'].some(key => response[key]?.some(item => !item || typeof item !== 'object' || Array.isArray(item)))
    || ['hotTopics', 'strategy'].some(key => response[key]?.some(item => typeof item !== 'string'))) {
    throw Object.assign(new Error('分析结果不完整，请重试'), { code: 'PARSE_ERROR' })
  }
  const focusAreas = Array.isArray(response?.focusAreas) ? response.focusAreas : []
  if (!focusAreas.length || response?.coreFocus) return response

  const priorityToWeight = {
    high: 35,
    medium: 25,
    low: 15
  }
  const priorityToFrequency = {
    high: '高',
    medium: '中',
    low: '低'
  }

  return {
    ...response,
    coreFocus: focusAreas.map((item) => ({
      dimensionKey: item.dimensionKey || item.type || '',
      name: item.label || item.type || '能力重点',
      weight: priorityToWeight[item.priority] || 20,
      desc: item.description || ''
    })),
    highFreqTypes: [],
    hotTopics: focusAreas.map((item) => item.label).filter(Boolean),
    strategy: focusAreas.map((item) => item.description).filter(Boolean)
  }
}

export async function getFocusAnalysis(data, options = {}) {
  const response = await request({
    url: '/targeted/focus',
    method: 'POST',
    data,
    timeout: FOCUS_TIMEOUT_MS,
    skipErrorHandler: true,
    signal: options.signal
  })
  return normalizeFocusAnalysis(response)
}

export async function getPositions() {
  return request({
    url: '/positions',
    method: 'GET'
  })
}

export async function generateQuestions(data) {
  const response = await request({
    url: '/targeted/generate',
    method: 'POST',
    data
  })
  return Array.isArray(response?.questions) ? response.questions : []
}

export async function getFocusAdminConfig(data) {
  return request({
    url: '/targeted/focus/admin',
    method: 'GET',
    data
  })
}

export async function saveFocusAdminConfig(data) {
  return request({
    url: '/targeted/focus/admin',
    method: 'PUT',
    data
  })
}

export async function disableFocusAdminConfig(data) {
  return request({
    url: '/targeted/focus/admin/disable',
    method: 'POST',
    data
  })
}
