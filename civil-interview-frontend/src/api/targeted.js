import { http } from './index'
import { getQuestionTypeName } from '@/utils/constants'

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
      name: item.label || getQuestionTypeName(item.type),
      weight: priorityToWeight[item.priority] || 20,
      desc: item.description || ''
    })),
    highFreqTypes: focusAreas.map((item) => ({
      type: getQuestionTypeName(item.type),
      frequency: priorityToFrequency[item.priority] || '中',
      example: item.description || item.label || ''
    })),
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
