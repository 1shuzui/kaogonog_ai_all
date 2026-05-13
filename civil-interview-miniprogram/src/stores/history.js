import { defineStore } from 'pinia'
import { getHistoryList, getHistoryStats, getHistoryTrend } from '../api/history'
import { normalizeListResponse } from '../utils/format'

export const useHistoryStore = defineStore('history', {
  state: () => ({
    records: [],
    stats: null,
    trendData: [],
    loading: false,
    lastQuery: {},
    pagination: {
      current: 1,
      pageSize: 10,
      total: 0
    }
  }),

  getters: {
    averageScore(state) {
      return Number(state.stats?.avgScore || 0)
    },
    bestScore(state) {
      return Number(state.stats?.bestScore || 0)
    },
    weakestDimension(state) {
      return state.stats?.weakestDimension || '暂无'
    }
  },

  actions: {
    async fetchRecords(params = {}) {
      this.loading = true
      try {
        const requestedPage = Number(params.current || params.page || this.pagination.current || 1)
        const query = {
          ...this.lastQuery,
          ...params,
          current: requestedPage,
          page: requestedPage,
          pageSize: Number(params.pageSize || this.pagination.pageSize || 10)
        }
        const response = await getHistoryList({
          ...query
        })
        const normalized = normalizeListResponse(response)
        this.records = normalized.list
        this.pagination.total = normalized.total
        this.pagination.current = requestedPage
        this.pagination.pageSize = query.pageSize
        this.lastQuery = {
          province: query.province || '',
          startDate: query.startDate || '',
          endDate: query.endDate || '',
          pageSize: query.pageSize
        }
      } finally {
        this.loading = false
      }
    },

    async fetchMore(params = {}) {
      const previous = [...this.records]
      await this.fetchRecords(params)
      const seen = new Set()
      this.records = [...previous, ...this.records].filter((item) => {
        const key = item.examId || `${item.date}:${item.questionSummary}`
        if (seen.has(key)) return false
        seen.add(key)
        return true
      })
    },

    async fetchStats() {
      this.stats = await getHistoryStats()
      return this.stats
    },

    async fetchTrend() {
      const response = await getHistoryTrend()
      this.trendData = Array.isArray(response) ? response : []
      return this.trendData
    }
  }
})
