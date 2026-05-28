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
