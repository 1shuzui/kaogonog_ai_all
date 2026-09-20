/**
 * 小程序定向备面状态仓库保存动态考试树、当前选择、重点分析和定向生成题。
 *
 * 考试体系可以声明自己的层级名称，例如法检先选岗位方向再选地区来源；方向也允许“不限”，用于按上级范围宽筛。
 * 重点分析必须来自真实题库统计或管理员发布内容，无数据时保留空态，不能用默认模板冒充分析。
 *
 * @param 无；actions 接收定向树节点、重点分析请求和生成题数量。
 * @return 导出 Pinia store，供定向备面、重点分析和管理员定向维护页复用。
 * @raises 不主动抛业务异常；接口失败由 action 或调用页面转成提示。
 */
import { defineStore } from 'pinia'
import { generateQuestions, getFocusAnalysis, getPositions, FOCUS_TIMEOUT_MS, FOCUS_SLOW_MS } from '../api/targeted'
import { DEFAULT_TARGETED_POSITION_TREE, normalizeTargetPayload } from '../utils/targetedOptions'
import { createCancellation } from '../utils/cancellation.mjs'

const focusJobs = new WeakMap()
let focusSequence = 0
const targetKey = payload => JSON.stringify(Object.entries(payload || {}).sort(([a], [b]) => a.localeCompare(b)))
const taskError = (message, code) => Object.assign(new Error(message), { code })

export const useTargetedStore = defineStore('targeted', {
  state: () => ({
    selectedProvince: '',
    selectedPosition: '',
    selectedTarget: null,
    positionTree: DEFAULT_TARGETED_POSITION_TREE,
    legacyPositions: [],
    positionsLoaded: false,
    focusData: null,
    generatedQuestions: [],
    focusLoading: false,
    focusStatus: 'idle',
    focusError: '',
    focusSlow: false,
    focusRequestId: 0,
    focusParams: null,
    generateLoading: false
  }),

  getters: {
    hasSelection(state) {
      if (state.selectedTarget?.targetCode) return true
      return !!state.selectedProvince && state.selectedPosition !== ''
    },
    selectionPayload(state) {
      if (state.selectedTarget?.targetCode) {
        return normalizeTargetPayload(state.selectedTarget)
      }
      return normalizeTargetPayload({
        province: state.selectedProvince,
        position: state.selectedPosition,
        targetCode: state.selectedPosition || state.selectedProvince,
        targetName: state.selectedPosition || state.selectedProvince
      })
    }
  },

  actions: {
    setSelection(province, position) {
      this.cancelFocusAnalysis()
      this.selectedProvince = province
      this.selectedPosition = position
      this.selectedTarget = null
      this.focusData = null
      this.focusParams = null
      this.focusStatus = 'idle'
      this.focusError = ''
      this.generatedQuestions = []
    },

    setTarget(target) {
      const payload = normalizeTargetPayload(target)
      if (targetKey(payload) === targetKey(this.selectedTarget)) return
      this.cancelFocusAnalysis()
      this.selectedTarget = payload
      this.selectedProvince = payload.province
      this.selectedPosition = payload.position
      this.focusData = null
      this.focusParams = null
      this.focusStatus = 'idle'
      this.focusError = ''
      this.generatedQuestions = []
    },

    async fetchPositionTree() {
      try {
        const response = await getPositions()
        const tree = Array.isArray(response?.tree) ? response.tree : []
        this.positionTree = tree.length ? tree : DEFAULT_TARGETED_POSITION_TREE
        this.legacyPositions = Array.isArray(response?.legacy) ? response.legacy : []
        this.positionsLoaded = true
      } catch (error) {
        this.positionTree = DEFAULT_TARGETED_POSITION_TREE
        this.positionsLoaded = false
      }
      return this.positionTree
    },

    cancelFocusAnalysis() {
      const job = focusJobs.get(this)
      if (!job) return
      if (this.focusRequestId === job.id) {
        this.focusRequestId = ++focusSequence
        this.focusLoading = false
        this.focusSlow = false
        this.focusStatus = 'cancelled'
        this.focusError = '已停止等待，可随时重试。服务端可能仍在处理本次请求。'
      }
      job.cancel()
    },

    fetchFocusAnalysis() {
      if (!this.hasSelection) {
        this.focusStatus = 'error'
        this.focusError = '请先选择考试方向'
        return Promise.resolve(null)
      }
      const payload = JSON.parse(JSON.stringify(this.selectionPayload))
      const key = targetKey(payload)
      const previous = focusJobs.get(this)
      if (previous && this.focusLoading && previous.key === key) return previous.promise
      this.cancelFocusAnalysis()
      const id = ++focusSequence
      this.focusRequestId = id
      this.focusParams = payload
      this.focusStatus = 'loading'
      this.focusLoading = true
      this.focusError = ''
      this.focusSlow = false
      const cancellation = createCancellation()
      const owns = () => this.focusRequestId === id && targetKey(this.selectionPayload) === key
      let slowTimer, deadline, rejectPending
      const pending = new Promise((resolve, reject) => { rejectPending = reject
        try { Promise.resolve(getFocusAnalysis(payload, { signal: cancellation.signal })).then(resolve, reject) }
        catch (error) { reject(error) }
      })
      const job = { id, key, cancel: () => {
        clearTimeout(slowTimer); clearTimeout(deadline)
        rejectPending(taskError('已停止等待', 'CANCELLED'))
        cancellation.cancel()
      } }
      slowTimer = setTimeout(() => { if (owns()) this.focusSlow = true }, FOCUS_SLOW_MS)
      deadline = setTimeout(() => {
        rejectPending(taskError('分析请求超时，请检查网络后重试', 'REQUEST_TIMEOUT'))
        cancellation.cancel()
      }, FOCUS_TIMEOUT_MS)
      job.promise = pending.then(data => {
        if (!owns()) return null
        this.focusData = data
        this.focusStatus = 'success'
        return data
      }, error => {
        if (!owns() || error?.code === 'CANCELLED') return null
        this.focusStatus = error?.code === 'REQUEST_TIMEOUT' ? 'timeout' : 'error'
        this.focusError = error?.message || '分析失败，请重试'
        throw error
      }).finally(() => {
        clearTimeout(slowTimer); clearTimeout(deadline)
        if (owns()) { this.focusLoading = false; this.focusSlow = false }
        if (focusJobs.get(this) === job) focusJobs.delete(this)
      })
      focusJobs.set(this, job)
      return job.promise
    },

    async fetchGeneratedQuestions(count = 5) {
      if (!this.hasSelection) return []
      this.generateLoading = true
      try {
        const response = await generateQuestions({
          ...this.selectionPayload,
          count,
          sourceMode: 'local'
        })
        this.generatedQuestions = Array.isArray(response) ? response : []
        return this.generatedQuestions
      } finally {
        this.generateLoading = false
      }
    }
  }
})
