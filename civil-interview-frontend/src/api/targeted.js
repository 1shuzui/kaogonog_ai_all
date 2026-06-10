/**
 * 定向备面接口封装，集中处理分类树、重点分析、专项生成和管理员发布内容。
 *
 * 定向分类采用动态层级，方向允许“不限”；重点分析只展示真实题库统计或管理员发布内容，
 * 无数据时由页面显示空态，不能在前端补通用模板。
 *
 * @param payload: 考试体系、地区/来源、方向、时间模式和题量等筛选字段。
 * @return Promise，解析分类树、重点分析、生成题目或管理员发布配置。
 * @raises AxiosError: 未登录、非管理员、题库无数据或接口失败会抛给调用页面。
 */
import { http } from './index'
function normalizeFocusAnalysis(response = {}) {
  const focusAreas = Array.isArray(response?.focusAreas) ? response.focusAreas : []
  if (!focusAreas.length || response?.coreFocus) {
    return response
  }

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

export async function getPositions() {
  return http.get('/positions')
}

export async function getFocusAnalysis(data) {
  const response = await http.post('/targeted/focus', data)
  return normalizeFocusAnalysis(response)
}

export async function getFocusAdminConfig(data) {
  return http.get('/targeted/focus/admin', { params: data })
}

export async function saveFocusAdminConfig(data) {
  return http.put('/targeted/focus/admin', data)
}

export async function disableFocusAdminConfig(data) {
  return http.post('/targeted/focus/admin/disable', data)
}

export async function generateQuestions(data) {
  const response = await http.post('/targeted/generate', data)
  return Array.isArray(response?.questions) ? response.questions : []
}
