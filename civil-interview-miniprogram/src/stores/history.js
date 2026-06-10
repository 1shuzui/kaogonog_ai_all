/**
 * 小程序历史记录状态仓库维护用户登录后的练习记录、趋势和统计摘要。
 *
 * 首页审核要求先浏览后登录，所以历史数据不能在启动阶段主动拉取；页面进入并确认登录后再读取个人记录。
 * 薄弱维度展示继续兼容旧口径，把“法治思维”显示为“行政思维”，但不修改后端历史原始字段。
 *
 * @param 无；actions 接收分页、日期和地区等查询条件。
 * @return 导出 Pinia store，供首页概览、历史列表和趋势图复用。
 * @raises 不主动抛业务异常；接口失败由 action 或调用页面转成提示。
 */
import { defineStore } from 'pinia'
import { getHistoryList, getHistoryStats, getHistoryTrend } from '../api/history'
import { normalizeListResponse } from '../utils/format'

const normalizeDimensionName = (name) => (name === '法治思维' ? '行政思维' : name)

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
      return normalizeDimensionName(state.stats?.weakestDimension || '暂无')
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
