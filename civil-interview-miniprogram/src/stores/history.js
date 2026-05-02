import { defineStore } from 'pinia'
import { getHistoryList, getHistoryStats, getHistoryTrend } from '../api/history'
import { normalizeListResponse } from '../utils/format'

export const useHistoryStore = defineStore('history', {
  state: () => ({
    records: [],
    stats: null,
    trendData: [],
    loading: false,
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
        const response = await getHistoryList({
          page: this.pagination.current,
          pageSize: this.pagination.pageSize,
          ...params
        })
        const normalized = normalizeListResponse(response)
        this.records = normalized.list
        this.pagination.total = normalized.total
        if (params.page) this.pagination.current = params.page
      } finally {
        this.loading = false
      }
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
