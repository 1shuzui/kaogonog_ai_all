/**
 * 小程序收藏与错题状态仓库服务移动端复盘，兼容旧缓存里 type 字段和新缓存里的显式标记。
 *
 * 低分题和手动收藏的来源不同，store 只做归一化展示，不把收藏状态当作错题证据，也不把错题自动写成收藏。
 * 本地存储异常只记录日志，避免复盘缓存影响录音、提交和评分主流程。
 *
 * @param 无；actions 接收题目摘要、分数、收藏类型和移除范围。
 * @return 导出 Pinia store，供错题本、收藏夹和再次练习入口复用。
 * @raises 不主动抛业务异常；接口失败由 action 或调用页面转成提示。
 */
import { defineStore } from 'pinia'
import { logger } from '../utils/logger'

const STORAGE_KEY = 'civil_favorites'
const USERNAME_STORAGE_KEY = 'username'

function currentStorageKey() {
  const username = String(uni.getStorageSync(USERNAME_STORAGE_KEY) || '').trim()
  return username ? `${STORAGE_KEY}:${username}` : STORAGE_KEY
}

function normalizeFavoriteItem(item) {
  if (!item || typeof item !== 'object') return null
  const hasExplicitFlags = item.isWeak !== undefined || item.isStarred !== undefined
  const score = Number(item.score)
  const maxScore = Number(item.maxScore)
  const lowScoreLegacy = Number.isFinite(score) && Number.isFinite(maxScore) && maxScore > 0
    ? score / maxScore < 0.6
    : item.type === 'weak'
  const isWeak = item.isWeak !== undefined
    ? Boolean(item.isWeak)
    : item.type === 'weak' && (hasExplicitFlags || lowScoreLegacy)
  const isStarred = item.isStarred !== undefined
    ? Boolean(item.isStarred)
    : item.type === 'starred' || item.type === 'favorite' || (!hasExplicitFlags && item.type === 'weak' && !lowScoreLegacy)
  return {
    ...item,
    isWeak,
    isStarred,
    type: isStarred ? 'starred' : isWeak ? 'weak' : item.type
  }
}

function loadItems() {
  try {
    const raw = uni.getStorageSync(currentStorageKey())
    const parsed = raw ? JSON.parse(raw) : []
    return Array.isArray(parsed) ? parsed.map(normalizeFavoriteItem).filter(Boolean) : []
  } catch {
    return []
  }
}

function saveItems(items) {
  try {
    uni.setStorageSync(currentStorageKey(), JSON.stringify(items))
  } catch (error) {
    logger.warn('Mini favorites storage write failed', {
      event: 'mini.favorites.storage.write_failed',
      error
    })
  }
}

export const useFavoritesStore = defineStore('favorites', {
  state: () => ({
    items: loadItems()
  }),

  getters: {
    count(state) {
      return state.items.filter((item) => item.isWeak || item.isStarred).length
    },
    weakItems(state) {
      return state.items.filter((item) => item.isWeak)
    },
    starredItems(state) {
      return state.items.filter((item) => item.isStarred)
    },
    isFavorited(state) {
      return (examId, questionId) => state.items.some((item) => (
        item.examId === examId && item.questionId === questionId && item.isStarred
      ))
    }
  },

  actions: {
    reloadForCurrentUser() {
      this.items = loadItems()
    },

    addItem({ examId, questionId, questionStem, dimension, score, maxScore, grade, date, type = 'weak' }) {
      if (!examId || !questionId) return
      const exists = this.items.find((item) => item.examId === examId && item.questionId === questionId)
      if (exists) {
        exists.questionStem = questionStem || exists.questionStem
        exists.dimension = dimension || exists.dimension
        exists.score = score ?? exists.score
        exists.maxScore = maxScore ?? exists.maxScore
        exists.grade = grade || exists.grade
        exists.date = date || exists.date
        exists.addedAt = exists.addedAt || new Date().toISOString()
        if (type === 'weak') exists.isWeak = true
        if (type === 'starred') exists.isStarred = true
        exists.type = exists.isStarred ? 'starred' : exists.isWeak ? 'weak' : type
      } else {
        this.items.unshift({
          id: `${examId}_${questionId}_${Date.now()}`,
          examId,
          questionId,
          questionStem,
          dimension,
          score,
          maxScore,
          grade,
          date: date || new Date().toISOString(),
          type,
          isWeak: type === 'weak',
          isStarred: type === 'starred',
          retryCount: 0,
          bestRetryScore: null,
          addedAt: new Date().toISOString()
        })
      }
      saveItems(this.items)
    },

    removeItem(id, type = 'all') {
      if (type === 'weak' || type === 'starred') {
        const item = this.items.find((entry) => entry.id === id)
        if (item) {
          if (type === 'weak') item.isWeak = false
          if (type === 'starred') item.isStarred = false
          item.type = item.isStarred ? 'starred' : item.isWeak ? 'weak' : ''
        }
        this.items = this.items.filter((item) => item.isWeak || item.isStarred)
      } else {
        this.items = this.items.filter((item) => item.id !== id)
      }
      saveItems(this.items)
    },

    clearAll() {
      this.items = []
      saveItems(this.items)
    }
  }
})
