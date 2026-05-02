import { defineStore } from 'pinia'
import { getQuestionById, getQuestions, getRandomQuestions } from '../api/questionBank'
import { normalizeListResponse } from '../utils/format'

export const useQuestionBankStore = defineStore('questionBank', {
  state: () => ({
    questions: [],
    currentQuestion: null,
    loading: false,
    filters: {
      keyword: '',
      dimension: '',
      province: 'national'
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
        const response = await getQuestions({
          page: this.pagination.current,
          pageSize: this.pagination.pageSize,
          ...this.filters,
          ...params
        })
        const normalized = normalizeListResponse(response)
        this.questions = normalized.list
        this.pagination.total = normalized.total
        if (params.page) this.pagination.current = params.page
      } finally {
        this.loading = false
      }
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
    }
  }
})
