import { defineStore } from 'pinia'
import { getHistoryList, getHistoryDetail, getHistoryTrend, getHistoryStats } from '@/api/history'

export const useHistoryStore = defineStore('history', {
  state: () => ({
    records: [],
    loading: false,
    pagination: { current: 1, pageSize: 10, total: 0 },
    trendData: [],
    stats: null
  }),

  getters: {
    averageScore(state) {
      return state.stats?.avgScore || 0
    },
    bestScore(state) {
      return state.stats?.bestScore || 0
    },
    weakestDimension(state) {
      return state.stats?.weakestDimension || ''
    }
  },

  actions: {
    async fetchRecords(params = {}) {
      this.loading = true
      try {
        const res = await getHistoryList({ ...this.pagination, ...params })
        this.records = res.list || res.data || []
        this.pagination.total = res.total || 0
        if (params.page) this.pagination.current = params.page
      } finally {
        this.loading = false
      }
    },

    async fetchDetail(examId) {
      return getHistoryDetail(examId)
    },

    async fetchTrend() {
      this.trendData = await getHistoryTrend()
    },

    async fetchStats() {
      this.stats = await getHistoryStats()
    }
  }
})
