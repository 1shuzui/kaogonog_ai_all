import { defineStore } from 'pinia'
import { getPositions, getFocusAnalysis, generateQuestions } from '@/api/targeted'

function buildGenerationMeta(questions = [], requestedMode = 'local') {
  const meta = {
    total: questions.length,
    localBankCount: 0,
    aiCount: 0,
    fallbackCount: 0,
    fallbackReason: '',
    questionSources: [],
    requestedMode
  }

  const sourceLabels = new Set()
  questions.forEach((item) => {
    if (item?.generationSource === 'llm') {
      meta.aiCount += 1
    } else if (item?.generationSource === 'fallback_bank') {
      meta.fallbackCount += 1
      meta.localBankCount += 1
    } else if (item?.generationSource === 'local_bank') {
      meta.localBankCount += 1
    }

    if (!meta.fallbackReason && item?.generationFallbackReason) {
      meta.fallbackReason = item.generationFallbackReason
    }
    if (item?.questionSourceLabel) {
      sourceLabels.add(item.questionSourceLabel)
    }
  })

  meta.questionSources = [...sourceLabels]
  return meta
}

export const useTargetedStore = defineStore('targeted', {
  state: () => ({
    selectedProvince: '',
    selectedPosition: '',
    focusData: null,
    focusLoading: false,
    generatedQuestions: [],
    generateLoading: false,
    generationMeta: null,
    generationMode: 'local'
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
      this.generationMeta = null
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

    async fetchGeneratedQuestions(count = 5, options = {}) {
      if (!this.hasSelection) return
      const sourceMode = options?.sourceMode || 'local'
      this.generateLoading = true
      this.generationMode = sourceMode
      try {
        const result = await generateQuestions({
          province: this.selectedProvince,
          position: this.selectedPosition,
          count
        }, sourceMode)
        this.generatedQuestions = result?.questions || []
        this.generationMeta = this.generatedQuestions.length
          ? buildGenerationMeta(this.generatedQuestions, sourceMode)
          : null
        return this.generatedQuestions
      } finally {
        this.generateLoading = false
      }
    }
  }
})
