/**
 * 这个状态仓库保存 `targeted` 相关跨页面状态；把它放在 Pinia 里，是为了切页面后仍能复用同一份数据。
 *
 * @param 无；文件级模块依赖导出函数、组合式 API 或调用方传入上下文。
 * @return 导出可复用的端侧能力，具体返回值由各公共函数保持兼容。
 * @raises 不主动吞掉业务异常；请求失败、权限不足和运行时错误交由调用方或全局拦截器处理。
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
