import { defineStore } from 'pinia'
import { createReviewStore } from '../../../shared/reviewStore.mjs'
import { reviewApi } from '../api/review'

export const useFavoritesStore = defineStore('favorites', createReviewStore({
  read: key => uni.getStorageSync(key),
  write: (key, value) => uni.setStorageSync(key, value),
  api: reviewApi
}))
