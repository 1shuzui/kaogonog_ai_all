/**
 * 这个状态仓库保存 `training` 相关跨页面状态；把它放在 Pinia 里，是为了切页面后仍能复用同一份数据。
 *
 * @param 无；文件级模块依赖导出函数、组合式 API 或调用方传入上下文。
 * @return 导出可复用的端侧能力，具体返回值由各公共函数保持兼容。
 * @raises 不主动吞掉业务异常；请求失败、权限不足和运行时错误交由调用方或全局拦截器处理。
 */
import { defineStore } from 'pinia'
import { logger } from '@/utils/logger'

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
    logger.warn('Training storage write failed', {
      event: 'training.storage.write_failed',
      error: e
    })
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
