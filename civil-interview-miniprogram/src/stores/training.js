/**
 * 小程序专项训练状态仓库保存题型训练进度和当前生成题目。
 *
 * 训练分类用于“综合分析、组织管理”等题型入口，不能拿来补足能力雷达或薄弱能力；评分能力维度由评分结果单独提供。
 * 本地进度只是移动端快速反馈，生成题目和权益扣减仍通过后端完成。
 *
 * @param 无；actions 接收训练分类、数量、省份和定向筛选参数。
 * @return 导出 Pinia store，供专项训练首页、题型训练页和结果记录复用。
 * @raises 不主动抛业务异常；接口失败由 action 或调用页面转成提示。
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
