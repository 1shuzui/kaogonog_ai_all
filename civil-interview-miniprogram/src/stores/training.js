import { defineStore } from 'pinia'
import { generateTrainingQuestions } from '../api/training'
import { TRAINING_PROGRESS_STORAGE_KEY } from '../utils/constants'

function loadProgress() {
  try {
    const raw = uni.getStorageSync(TRAINING_PROGRESS_STORAGE_KEY)
    return raw ? JSON.parse(raw) : {}
  } catch {
    return {}
  }
}

function saveProgress(progress) {
  uni.setStorageSync(TRAINING_PROGRESS_STORAGE_KEY, JSON.stringify(progress))
}

function defaultProgress() {
  return {
    attempts: 0,
    totalScore: 0,
    bestScore: 0,
    recentScores: [],
    lastPracticeDate: ''
  }
}

export const useTrainingStore = defineStore('training', {
  state: () => ({
    progress: loadProgress(),
    generatedQuestions: [],
    generating: false
  }),

  getters: {
    getDimensionProgress(state) {
      return (key) => state.progress[key] || defaultProgress()
    }
  },

  actions: {
    async generate(dimension, count = 1) {
      this.generating = true
      try {
        const response = await generateTrainingQuestions({ dimension, count })
        this.generatedQuestions = Array.isArray(response) ? response : []
        return this.generatedQuestions
      } finally {
        this.generating = false
      }
    },

    recordResult(key, score) {
      const current = this.progress[key] || defaultProgress()
      const value = Math.round(Number(score || 0))
      current.attempts += 1
      current.totalScore += value
      current.bestScore = Math.max(current.bestScore, value)
      current.recentScores = [...current.recentScores, value].slice(-10)
      current.lastPracticeDate = new Date().toISOString()
      this.progress = {
        ...this.progress,
        [key]: current
      }
      saveProgress(this.progress)
    }
  }
})
