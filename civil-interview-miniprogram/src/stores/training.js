/**
 * 这个状态仓库保存 `training` 相关跨页面状态；把它放在 Pinia 里，是为了切页面后仍能复用同一份数据。
 *
 * @param 无；文件级模块依赖导出函数、组合式 API 或调用方传入上下文。
 * @return 导出可复用的端侧能力，具体返回值由各公共函数保持兼容。
 * @raises 不主动吞掉业务异常；请求失败、权限不足和运行时错误交由调用方或全局拦截器处理。
 */
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
    async generate(dimension, count = 1, province = 'national', extraFilters = {}) {
      this.generating = true
      try {
        const response = await generateTrainingQuestions({ dimension, province, count, sourceMode: 'local', ...extraFilters })
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
