/**
 * PC 历史记录状态仓库维护账号维度的练习记录、趋势和统计摘要。
 *
 * 历史数据是评分结果的回放，不能被前端根据本地收藏或当前题目重新推算；薄弱维度仍保留“法治思维”到“行政思维”的兼容映射。
 * 这些数据只在用户登录后使用，避免把个人练习轨迹暴露给未登录浏览页面。
 *
 * @param 无；actions 接收分页、日期和省份等历史查询条件。
 * @return 导出 Pinia store，供历史列表、首页概览和能力趋势组件复用。
 * @raises 不主动抛业务异常；接口失败由 action 或调用页面转成提示。
 */
import { defineStore } from 'pinia'
import { getHistoryList, getHistoryDetail, getHistoryTrend, getHistoryStats } from '@/api/history'

const normalizeDimensionName = (name) => (name === '法治思维' ? '行政思维' : name)

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
      return normalizeDimensionName(state.stats?.weakestDimension || '')
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
