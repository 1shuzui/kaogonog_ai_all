/**
 * PC 专项训练状态仓库保存题型训练进度，训练分类只用于出题入口，不代表评分能力维度。
 *
 * 进度放在本地是为了给专项入口提供轻量反馈；正式题目生成、权益消耗和评分结果仍以后端流程为准。
 * 后续若接入服务端训练统计，要继续保持“题型分类”和“行政思维等能力维度”两套口径。
 *
 * @param 无；actions 接收训练分类 key 和本次得分。
 * @return 导出 Pinia store，供专项训练入口和训练结果记录复用。
 * @raises 不主动抛业务异常；接口失败由 action 或调用页面转成提示。
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
