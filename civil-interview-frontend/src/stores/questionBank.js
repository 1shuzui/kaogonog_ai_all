/**
 * PC 题库状态仓库集中保存筛选条件、分页列表和管理员编辑后的刷新状态。
 *
 * 题库真实分类以后端题目元数据为准，前端只提交筛选条件；不能在 store 里用省份、岗位名或题型关键词重写考试体系。
 * 管理员新增或编辑后立即重新拉列表，是为了让分类复核、采分点和关键词提示能尽快暴露，而不是在本地乐观伪造题库结果。
 *
 * @param 无；actions 接收筛选条件、题目表单或导入文件。
 * @return 导出 Pinia store，供题库列表、题库编辑和导入页共享题库状态。
 * @raises 不主动抛业务异常；接口失败由 action 或调用页面转成提示。
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
