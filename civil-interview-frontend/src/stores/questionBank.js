/**
 * 这个状态仓库保存 `questionBank` 相关跨页面状态；把它放在 Pinia 里，是为了切页面后仍能复用同一份数据。
 *
 * @param 无；文件级模块依赖导出函数、组合式 API 或调用方传入上下文。
 * @return 导出可复用的端侧能力，具体返回值由各公共函数保持兼容。
 * @raises 不主动吞掉业务异常；请求失败、权限不足和运行时错误交由调用方或全局拦截器处理。
 */
import { defineStore } from 'pinia'
import { getQuestions, createQuestion, updateQuestion, deleteQuestion, importQuestions } from '@/api/questionBank'

export const useQuestionBankStore = defineStore('questionBank', {
  state: () => ({
    questions: [],
    loading: false,
    pagination: { current: 1, pageSize: 10, total: 0 },
    filters: { keyword: '', dimension: '', province: 'national', position: '', subcategory: '', subcategory2: '', examCategory: '', year: '', categoryReview: '' }
  }),

  getters: {
    filteredQuestions(state) {
      return state.questions
    }
  },

  actions: {
    async fetchQuestions(params = {}) {
      this.loading = true
      try {
        const nextCurrent = Number(params.current || params.page || this.pagination.current || 1)
        const nextPageSize = Number(params.pageSize || this.pagination.pageSize || 10)
        this.pagination.current = nextCurrent
        this.pagination.pageSize = nextPageSize
        const mergedParams = {
          ...this.filters,
          ...params,
          current: nextCurrent,
          pageSize: nextPageSize
        }
        const res = await getQuestions(mergedParams)
        this.questions = Array.isArray(res?.list) ? res.list : []
        this.pagination.total = Number(res?.total ?? this.questions.length)
      } finally {
        this.loading = false
      }
    },

    setFilters(filters) {
      Object.assign(this.filters, filters)
      this.pagination.current = 1
    },

    switchProvince(code) {
      this.filters.province = code
      this.pagination.current = 1
      return this.fetchQuestions()
    },

    async addQuestion(data) {
      const result = await createQuestion(data)
      await this.fetchQuestions()
      return result
    },

    async editQuestion(id, data) {
      const result = await updateQuestion(id, data)
      await this.fetchQuestions()
      return result
    },

    async removeQuestion(id) {
      await deleteQuestion(id)
      await this.fetchQuestions()
    },

    async importFromFile(file) {
      const result = await importQuestions(file)
      await this.fetchQuestions()
      return result
    }
  }
})
