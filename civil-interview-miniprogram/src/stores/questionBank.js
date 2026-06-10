/**
 * 小程序题库状态仓库保存移动端筛选、分页列表和当前题目详情。
 *
 * 未登录用户可先浏览筛选结构，但真实题目检索、随机抽题和详情练习仍要经过接口权限；store 不负责绕过权益校验。
 * 考试分类、地区、岗位和题型分类只作为查询条件传给后端，不能在端侧重新给题目定类。
 *
 * @param 无；actions 接收筛选条件、题目 id 或随机抽题参数。
 * @return 导出 Pinia store，供题库列表、题目详情和移动端管理员题库页复用。
 * @raises 不主动抛业务异常；接口失败由 action 或调用页面转成提示。
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
