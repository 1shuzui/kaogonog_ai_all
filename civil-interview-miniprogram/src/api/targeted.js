/**
 * 这个接口文件负责定向备面分类和重点分析接口封装；页面只调用这里的方法，避免到处拼 URL 和重复处理错误。
 *
 * @param 无；文件级模块依赖导出函数、组合式 API 或调用方传入上下文。
 * @return 导出可复用的端侧能力，具体返回值由各公共函数保持兼容。
 * @raises 不主动吞掉业务异常；请求失败、权限不足和运行时错误交由调用方或全局拦截器处理。
 */
import { request } from './request'

function normalizeFocusAnalysis(response = {}) {
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

export async function getFocusAnalysis(data) {
  const response = await request({
    url: '/targeted/focus',
    method: 'POST',
    data
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
