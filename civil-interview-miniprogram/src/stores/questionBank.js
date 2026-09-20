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

// Outside resettable state: a pre-reset request must never match a new request (ABA).
let nextListRequestId = 0

async function fetchList(store, params, append = false) {
  const requestId = ++nextListRequestId
  store._listRequestId = requestId
  const previous = append ? [...store.questions] : []
  const requestedPage = Number(params.current || params.page || store.pagination.current || 1)
  store.loading = true
  store.error = ''
  try {
    const response = await getQuestions({
      pageSize: store.pagination.pageSize,
      ...store.filters,
      ...params,
      current: requestedPage,
      page: requestedPage
    })
    if (store._listRequestId !== requestId) return
    const normalized = normalizeListResponse(response)
    const seen = new Set()
    store.questions = append ? [...previous, ...normalized.list].filter((item) => {
      const key = item.id || item.stem
      if (seen.has(key)) return false
      seen.add(key)
      return true
    }) : normalized.list
    store.pagination.total = normalized.total
    store.pagination.current = requestedPage
    return true
  } catch (cause) {
    if (store._listRequestId !== requestId) return
    store.error = cause?.message || '题目暂时无法加载，请重试'
    throw cause
  } finally {
    if (store._listRequestId === requestId) store.loading = false
  }
}

export const useQuestionBankStore = defineStore('questionBank', {
  state: () => ({
    questions: [],
    currentQuestion: null,
    loading: false,
    error: '',
    _listRequestId: 0,
    filtersInitialized: false,
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
      return fetchList(this, params)
    },

    async fetchMore(params = {}) {
      return fetchList(this, params, true)
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
      this.filtersInitialized = true
      this._listRequestId = ++nextListRequestId
      this.loading = false
      this.error = ''
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
