import { defineStore } from 'pinia'
import { generateQuestions, getFocusAnalysis } from '../api/targeted'

export const useTargetedStore = defineStore('targeted', {
  state: () => ({
    selectedProvince: '',
    selectedPosition: '',
    focusData: null,
    generatedQuestions: [],
    focusLoading: false,
    generateLoading: false
  }),

  getters: {
    hasSelection(state) {
      return !!state.selectedProvince && !!state.selectedPosition
    }
  },

  actions: {
    setSelection(province, position) {
      this.selectedProvince = province
      this.selectedPosition = position
      this.focusData = null
    },

    async fetchFocusAnalysis() {
      if (!this.hasSelection) return null
      this.focusLoading = true
      try {
        this.focusData = await getFocusAnalysis({
          province: this.selectedProvince,
          position: this.selectedPosition
        })
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
          province: this.selectedProvince,
          position: this.selectedPosition,
          count
        })
        this.generatedQuestions = Array.isArray(response) ? response : []
        return this.generatedQuestions
      } finally {
        this.generateLoading = false
      }
    }
  }
})
