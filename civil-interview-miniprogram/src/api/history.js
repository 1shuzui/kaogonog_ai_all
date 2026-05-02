import { request } from './request'

export function getHistoryList(params = {}) {
  return request({
    url: '/history',
    data: params
  })
}

export function getHistoryDetail(examId) {
  return request({
    url: `/history/${examId}`
  })
}

export function getHistoryTrend(days = 30) {
  return request({
    url: '/history/trend',
    data: { days }
  })
}

export function getHistoryStats() {
  return request({
    url: '/history/stats'
  })
}
