/**
 * PC 收藏与错题状态仓库保留用户复盘入口，兼容旧数据中用 type 表示收藏或低分题的记录。
 *
 * 低分错题来自评分结果，手动收藏来自用户操作，store 只做旧格式归一和本地展示，不能把收藏状态反推成评分表现。
 * 本地存储失败时只记录告警，避免因为复盘入口异常影响正式答题和评分。
 *
 * @param 无；actions 接收题目摘要、得分、收藏类型和移除范围。
 * @return 导出 Pinia store，供错题本、收藏按钮和再次练习入口复用。
 * @raises 不主动抛业务异常；接口失败由 action 或调用页面转成提示。
 */
import { defineStore } from 'pinia'
import { logger } from '@/utils/logger'

const STORAGE_KEY = 'civil_favorites'
const USERNAME_STORAGE_KEY = 'username'

function currentStorageKey() {
  const username = String(localStorage.getItem(USERNAME_STORAGE_KEY) || '').trim()
  return username ? `${STORAGE_KEY}:${username}` : STORAGE_KEY
}

function loadFromStorage() {
  try {
    const key = currentStorageKey()
    const data = localStorage.getItem(key)
    const parsed = data ? JSON.parse(data) : []
    const normalized = Array.isArray(parsed) ? parsed.map(normalizeFavoriteItem).filter(Boolean) : []
    if (JSON.stringify(parsed) !== JSON.stringify(normalized)) {
      saveToStorage(normalized)
    }
    return normalized
  } catch {
    return []
  }
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
  const type = isStarred ? 'starred' : isWeak ? 'weak' : item.type
  return {
    ...item,
    isWeak,
    isStarred,
    type
  }
}

function saveToStorage(items) {
  try {
    localStorage.setItem(currentStorageKey(), JSON.stringify(items))
  } catch (e) {
    logger.warn('Favorites storage write failed', {
      event: 'favorites.storage.write_failed',
      error: e
    })
  }
}

export const useFavoritesStore = defineStore('favorites', {
  state: () => ({
    items: loadFromStorage()
  }),

  getters: {
    count(state) {
      return state.items.filter(i => i.isWeak || i.isStarred).length
    },
    weakItems(state) {
      return state.items.filter(i => i.isWeak)
    },
    starredItems(state) {
      return state.items.filter(i => i.isStarred)
    },
    isFavorited(state) {
      return (examId, questionId) =>
        state.items.some(i => i.examId === examId && i.questionId === questionId && i.isStarred)
    }
  },

  actions: {
    reloadForCurrentUser() {
      this.items = loadFromStorage()
    },

    addItem({ examId, questionId, questionStem, dimension, score, maxScore, grade, date, type = 'weak' }) {
      const exists = this.items.find(i => i.examId === examId && i.questionId === questionId)
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
      saveToStorage(this.items)
    },

    removeItem(id, type = 'all') {
      if (type === 'weak' || type === 'starred') {
        const item = this.items.find(i => i.id === id)
        if (item) {
          if (type === 'weak') item.isWeak = false
          if (type === 'starred') item.isStarred = false
          item.type = item.isStarred ? 'starred' : item.isWeak ? 'weak' : ''
        }
        this.items = this.items.filter(i => i.isWeak || i.isStarred)
      } else {
        this.items = this.items.filter(i => i.id !== id)
      }
      saveToStorage(this.items)
    },

    updateRetry(id, score) {
      const item = this.items.find(i => i.id === id)
      if (item) {
        item.retryCount++
        if (item.bestRetryScore === null || score > item.bestRetryScore) {
          item.bestRetryScore = score
        }
        saveToStorage(this.items)
      }
    },

    clearAll() {
      this.items = []
      saveToStorage(this.items)
    }
  }
})
