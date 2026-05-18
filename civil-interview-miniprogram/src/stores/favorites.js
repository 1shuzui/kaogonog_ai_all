import { defineStore } from 'pinia'
import { logger } from '../utils/logger'

const STORAGE_KEY = 'civil_favorites'

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
    const raw = uni.getStorageSync(STORAGE_KEY)
    const parsed = raw ? JSON.parse(raw) : []
    return Array.isArray(parsed) ? parsed.map(normalizeFavoriteItem).filter(Boolean) : []
  } catch {
    return []
  }
}

function saveItems(items) {
  try {
    uni.setStorageSync(STORAGE_KEY, JSON.stringify(items))
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
