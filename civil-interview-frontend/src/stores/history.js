/**
 * 这个状态仓库保存 `history` 相关跨页面状态；把它放在 Pinia 里，是为了切页面后仍能复用同一份数据。
 *
 * @param 无；文件级模块依赖导出函数、组合式 API 或调用方传入上下文。
 * @return 导出可复用的端侧能力，具体返回值由各公共函数保持兼容。
 * @raises 不主动吞掉业务异常；请求失败、权限不足和运行时错误交由调用方或全局拦截器处理。
 */
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
        if (params.page || params.current) this.pagination.current = Number(params.page || params.current)
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
