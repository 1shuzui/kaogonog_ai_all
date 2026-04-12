import { defineStore } from 'pinia'
import { getPositions, getFocusAnalysis, generateQuestions } from '@/api/targeted'

export const useTargetedStore = defineStore('targeted', {
  state: () => ({
    selectedProvince: '',
    selectedPosition: '',
    focusData: null,
    focusLoading: false,
    generatedQuestions: [],
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
      this.generatedQuestions = []
    },

    async fetchFocusAnalysis() {
      if (!this.hasSelection) return
      this.focusLoading = true
      try {
        this.focusData = await getFocusAnalysis({
          province: this.selectedProvince,
          position: this.selectedPosition
        })
      } finally {
        this.focusLoading = false
      }
    },

    async fetchGeneratedQuestions(count = 5) {
      if (!this.hasSelection) return
      this.generateLoading = true
      try {
        this.generatedQuestions = await generateQuestions({
          province: this.selectedProvince,
          position: this.selectedPosition,
          count
        })
      } finally {
        this.generateLoading = false
      }
    }
  }
})
