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
      name: item.label || item.type || '能力重点',
      weight: priorityToWeight[item.priority] || 20,
      desc: item.description || ''
    })),
    highFreqTypes: focusAreas.map((item) => ({
      type: item.label || item.type || '高频题型',
      frequency: priorityToFrequency[item.priority] || '中',
      example: item.description || item.label || ''
    })),
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
