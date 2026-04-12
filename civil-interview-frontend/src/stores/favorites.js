import { defineStore } from 'pinia'

const STORAGE_KEY = 'civil_favorites'

function loadFromStorage() {
  try {
    const data = localStorage.getItem(STORAGE_KEY)
    return data ? JSON.parse(data) : []
  } catch {
    return []
  }
}

function saveToStorage(items) {
  try {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(items))
  } catch (e) {
    console.warn('[Favorites] localStorage 存储失败:', e.message)
  }
}

export const useFavoritesStore = defineStore('favorites', {
  state: () => ({
    items: loadFromStorage()
  }),

  getters: {
    count(state) {
      return state.items.length
    },
    weakItems(state) {
      return state.items.filter(i => i.type === 'weak')
    },
    starredItems(state) {
      return state.items.filter(i => i.type === 'starred')
    },
    isFavorited(state) {
      return (examId, questionId) =>
        state.items.some(i => i.examId === examId && i.questionId === questionId)
    }
  },

  actions: {
    addItem({ examId, questionId, questionStem, dimension, score, maxScore, grade, date, type = 'weak' }) {
      const exists = this.items.find(i => i.examId === examId && i.questionId === questionId)
      if (exists) {
        exists.type = type
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
          retryCount: 0,
          bestRetryScore: null,
          addedAt: new Date().toISOString()
        })
      }
      saveToStorage(this.items)
    },

    removeItem(id) {
      this.items = this.items.filter(i => i.id !== id)
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
