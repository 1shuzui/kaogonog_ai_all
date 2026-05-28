import { defineStore } from 'pinia'
import { getPositions, getFocusAnalysis, generateQuestions } from '@/api/targeted'
import { DEFAULT_TARGETED_POSITION_TREE, normalizeTargetPayload } from '@/utils/targetedOptions'

export const useTargetedStore = defineStore('targeted', {
  state: () => ({
    selectedProvince: '',
    selectedPosition: '',
    selectedTarget: null,
    positionTree: DEFAULT_TARGETED_POSITION_TREE,
    legacyPositions: [],
    positionsLoaded: false,
    focusData: null,
    focusLoading: false,
    generatedQuestions: [],
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
      if (!this.hasSelection) return
      this.focusLoading = true
      try {
        this.focusData = await getFocusAnalysis(this.selectionPayload)
      } finally {
        this.focusLoading = false
      }
    },

    async fetchGeneratedQuestions(count = 5) {
      if (!this.hasSelection) return
      this.generateLoading = true
      try {
        this.generatedQuestions = await generateQuestions({
          ...this.selectionPayload,
          count,
          sourceMode: 'local'
        })
        return this.generatedQuestions
      } finally {
        this.generateLoading = false
      }
    }
  }
})
