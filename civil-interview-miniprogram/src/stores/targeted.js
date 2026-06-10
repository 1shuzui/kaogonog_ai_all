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
import { generateQuestions, getFocusAnalysis, getPositions } from '../api/targeted'
import { DEFAULT_TARGETED_POSITION_TREE, normalizeTargetPayload } from '../utils/targetedOptions'

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
      this.selectedProvince = province
      this.selectedPosition = position
      this.selectedTarget = null
      this.focusData = null
      this.generatedQuestions = []
    },

    setTarget(target) {
      const payload = normalizeTargetPayload(target)
      this.selectedTarget = payload
      this.selectedProvince = payload.province
      this.selectedPosition = payload.position
      this.focusData = null
      this.generatedQuestions = []
    },

    async fetchPositionTree() {
      try {
        const response = await getPositions()
        const tree = Array.isArray(response?.tree) ? response.tree : []
        this.positionTree = tree.length ? tree : DEFAULT_TARGETED_POSITION_TREE
        this.legacyPositions = Array.isArray(response?.legacy) ? response.legacy : []
      } catch (error) {
        this.positionTree = DEFAULT_TARGETED_POSITION_TREE
      } finally {
        this.positionsLoaded = true
      }
      return this.positionTree
    },

    async fetchFocusAnalysis() {
      if (!this.hasSelection) return null
      this.focusLoading = true
      try {
        this.focusData = await getFocusAnalysis(this.selectionPayload)
        return this.focusData
      } finally {
        this.focusLoading = false
      }
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
