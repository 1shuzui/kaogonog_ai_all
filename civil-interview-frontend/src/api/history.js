import { http } from './index'

export async function getHistoryList(params) {
  return http.get('/history', { params })
}

export async function getHistoryDetail(examId) {
  return http.get(`/history/${examId}`)
}

export async function getHistoryTrend(days = 30) {
  return http.get('/history/trend', { params: { days } })
}

export async function getHistoryStats() {
  return http.get('/history/stats')
}
