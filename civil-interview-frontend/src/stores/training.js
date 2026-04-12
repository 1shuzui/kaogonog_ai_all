import { defineStore } from 'pinia'

const STORAGE_KEY = 'civil_training_progress'

function loadProgress() {
  try {
    const data = localStorage.getItem(STORAGE_KEY)
    return data ? JSON.parse(data) : {}
  } catch {
    return {}
  }
}

function saveProgress(progress) {
  try {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(progress))
  } catch (e) {
    console.warn('[Training] localStorage 存储失败:', e.message)
  }
}

export const useTrainingStore = defineStore('training', {
  state: () => ({
    progress: loadProgress(),
    generating: false
  }),

  getters: {
    getDimensionProgress(state) {
      return (dimensionKey) => state.progress[dimensionKey] || {
        attempts: 0,
        totalScore: 0,
        bestScore: 0,
        recentScores: [],
        lastPracticeDate: null
      }
    },
    allDimensionProgress(state) {
      return state.progress
    }
  },

  actions: {
    recordTrainingResult(dimensionKey, score) {
      if (!this.progress[dimensionKey]) {
        this.progress[dimensionKey] = {
          attempts: 0,
          totalScore: 0,
          bestScore: 0,
          recentScores: [],
          lastPracticeDate: null
        }
      }
      const p = this.progress[dimensionKey]
      p.attempts++
      p.totalScore += score
      p.bestScore = Math.max(p.bestScore, score)
      p.recentScores.push(score)
      if (p.recentScores.length > 10) p.recentScores.shift()
      p.lastPracticeDate = new Date().toISOString()
      saveProgress(this.progress)
    }
  }
})
