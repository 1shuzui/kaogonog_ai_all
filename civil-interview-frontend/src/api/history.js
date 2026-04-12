import { http, USE_MOCK } from './index'
import { getMockHistory, getMockHistoryDetail, getMockTrend, getMockStats } from './mock/history'

export async function getHistoryList(params) {
  if (USE_MOCK) return getMockHistory(params)
  return http.get('/history', { params })
}

export async function getHistoryDetail(examId) {
  if (USE_MOCK) return getMockHistoryDetail(examId)
  return http.get(`/history/${examId}`)
}

export async function getHistoryTrend(days = 30) {
  if (USE_MOCK) return getMockTrend()
  return http.get('/history/trend', { params: { days } })
}

export async function getHistoryStats() {
  if (USE_MOCK) return getMockStats()
  return http.get('/history/stats')
}
