import { defineStore } from 'pinia'
import { getQuestions, createQuestion, updateQuestion, deleteQuestion, importQuestions } from '@/api/questionBank'

export const useQuestionBankStore = defineStore('questionBank', {
  state: () => ({
    questions: [],
    loading: false,
    pagination: { current: 1, pageSize: 10, total: 0 },
    filters: { keyword: '', dimension: '', province: 'national' }
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
        const mergedParams = { ...this.filters, ...this.pagination, ...params }
        const res = await getQuestions(mergedParams)
        this.questions = res.list
        this.pagination.total = res.total
        if (params.page) this.pagination.current = params.page
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
