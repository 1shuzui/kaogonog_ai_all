import { defineStore } from 'pinia'
import { createReviewStore } from '../../../shared/reviewStore.mjs'
import { reviewApi } from '../api/review'

export const useFavoritesStore = defineStore('favorites', createReviewStore({
  read: key => localStorage.getItem(key),
  write: (key, value) => localStorage.setItem(key, value),
  api: reviewApi
}))
