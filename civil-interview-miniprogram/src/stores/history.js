/**
 * 这个状态仓库保存 `history` 相关跨页面状态；把它放在 Pinia 里，是为了切页面后仍能复用同一份数据。
 *
 * @param 无；文件级模块依赖导出函数、组合式 API 或调用方传入上下文。
 * @return 导出可复用的端侧能力，具体返回值由各公共函数保持兼容。
 * @raises 不主动吞掉业务异常；请求失败、权限不足和运行时错误交由调用方或全局拦截器处理。
 */
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
