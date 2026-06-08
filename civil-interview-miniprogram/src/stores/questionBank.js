/**
 * 这个状态仓库保存 `questionBank` 相关跨页面状态；把它放在 Pinia 里，是为了切页面后仍能复用同一份数据。
 *
 * @param 无；文件级模块依赖导出函数、组合式 API 或调用方传入上下文。
 * @return 导出可复用的端侧能力，具体返回值由各公共函数保持兼容。
 * @raises 不主动吞掉业务异常；请求失败、权限不足和运行时错误交由调用方或全局拦截器处理。
 */
import { defineStore } from 'pinia'
import { deleteQuestion, getQuestionById, getQuestions, getRandomQuestions } from '../api/questionBank'
import { normalizeListResponse } from '../utils/format'

export const useQuestionBankStore = defineStore('questionBank', {
  state: () => ({
    questions: [],
    currentQuestion: null,
    loading: false,
    filters: {
      keyword: '',
      dimension: '',
      province: 'national',
      position: '',
      examCategory: '',
      subcategory: '',
      subcategory2: '',
      year: ''
    },
    pagination: {
      current: 1,
      pageSize: 10,
      total: 0
    }
  }),

  actions: {
    async fetchQuestions(params = {}) {
      this.loading = true
      try {
        const requestedPage = Number(params.current || params.page || this.pagination.current || 1)
        const response = await getQuestions({
          current: requestedPage,
          page: requestedPage,
          pageSize: this.pagination.pageSize,
          ...this.filters,
          ...params
        })
        const normalized = normalizeListResponse(response)
        this.questions = normalized.list
        this.pagination.total = normalized.total
        this.pagination.current = requestedPage
      } finally {
        this.loading = false
      }
    },

    async fetchMore(params = {}) {
      const previous = [...this.questions]
      await this.fetchQuestions(params)
      const seen = new Set()
      this.questions = [...previous, ...this.questions].filter((item) => {
        const key = item.id || item.stem
        if (seen.has(key)) return false
        seen.add(key)
        return true
      })
    },

    async fetchQuestion(id) {
      this.currentQuestion = await getQuestionById(id)
      return this.currentQuestion
    },

    async fetchRandom(params = {}) {
      const response = await getRandomQuestions(params)
      return Array.isArray(response) ? response : normalizeListResponse(response).list
    },

    setFilters(filters = {}) {
      this.filters = {
        ...this.filters,
        ...filters
      }
      this.pagination.current = 1
    },

    async removeQuestion(id) {
      await deleteQuestion(id)
      this.questions = this.questions.filter((q) => q.id !== id)
    }
  }
})
