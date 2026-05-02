import { defineStore } from 'pinia'
import { login as loginApi, register as registerApi } from '../api/auth'
import { getProvinces, getUserInfo, updatePreferences } from '../api/user'
import {
  DEFAULT_PREFERENCES,
  PREFERENCES_STORAGE_KEY,
  PROVINCE_STORAGE_KEY,
  PROVINCES,
  TOKEN_STORAGE_KEY,
  USERNAME_STORAGE_KEY
} from '../utils/constants'

function readStorage(key, fallback = '') {
  try {
    const value = uni.getStorageSync(key)
    return value === '' || value === undefined ? fallback : value
  } catch {
    return fallback
  }
}

function readJsonStorage(key, fallback) {
  try {
    const value = uni.getStorageSync(key)
    if (!value) return fallback
    return typeof value === 'string' ? JSON.parse(value) : value
  } catch {
    return fallback
  }
}

function normalizePreferences(preferences = {}) {
  const merged = {
    ...DEFAULT_PREFERENCES,
    ...(preferences || {})
  }
  return {
    defaultPrepTime: Math.max(30, Number(merged.defaultPrepTime) || DEFAULT_PREFERENCES.defaultPrepTime),
    defaultAnswerTime: Math.max(60, Number(merged.defaultAnswerTime) || DEFAULT_PREFERENCES.defaultAnswerTime),
    enableAudio: merged.enableAudio !== false
  }
}

export const useUserStore = defineStore('user', {
  state: () => ({
    token: readStorage(TOKEN_STORAGE_KEY, ''),
    username: readStorage(USERNAME_STORAGE_KEY, ''),
    userInfo: {
      id: '',
      name: '',
      avatar: '',
      province: readStorage(PROVINCE_STORAGE_KEY, 'national'),
      role: 'user',
      isAdmin: false
    },
    selectedProvince: readStorage(PROVINCE_STORAGE_KEY, 'national'),
    provinces: PROVINCES,
    preferences: normalizePreferences(readJsonStorage(PREFERENCES_STORAGE_KEY, DEFAULT_PREFERENCES))
  }),

  getters: {
    isAuthenticated(state) {
      return !!state.token
    },
    displayName(state) {
      return state.userInfo?.name || state.username || '考生'
    },
    selectedProvinceName(state) {
      return state.provinces.find((item) => item.code === state.selectedProvince)?.name || '国考'
    }
  },

  actions: {
    async login(username, password) {
      const response = await loginApi(username, password)
      this.token = response.access_token
      this.username = username
      uni.setStorageSync(TOKEN_STORAGE_KEY, response.access_token)
      uni.setStorageSync(USERNAME_STORAGE_KEY, username)
      await this.loadUserInfo().catch(() => null)
      return response
    },

    async register(form) {
      return registerApi(form)
    },

    logout() {
      this.token = ''
      this.username = ''
      this.userInfo = {
        id: '',
        name: '',
        avatar: '',
        province: 'national',
        role: 'user',
        isAdmin: false
      }
      uni.removeStorageSync(TOKEN_STORAGE_KEY)
      uni.removeStorageSync(USERNAME_STORAGE_KEY)
    },

    async loadUserInfo() {
      const info = await getUserInfo({ skipErrorHandler: true })
      const username = info?.id || this.username
      this.username = username
      if (username) uni.setStorageSync(USERNAME_STORAGE_KEY, username)

      this.userInfo = {
        id: username,
        name: info?.name || username || '考生',
        avatar: info?.avatar || '',
        province: info?.province || this.selectedProvince || 'national',
        role: info?.role || 'user',
        isAdmin: !!info?.isAdmin || username === 'admin'
      }
      if (info?.province) this.setProvince(info.province)
      if (info?.preferences) {
        this.preferences = normalizePreferences({
          ...this.preferences,
          ...info.preferences
        })
        uni.setStorageSync(PREFERENCES_STORAGE_KEY, JSON.stringify(this.preferences))
      }
      return this.userInfo
    },

    async loadProvinces() {
      try {
        const response = await getProvinces()
        if (Array.isArray(response) && response.length) {
          this.provinces = response
        }
      } catch {
        this.provinces = PROVINCES
      }
      return this.provinces
    },

    setProvince(code) {
      this.selectedProvince = code || 'national'
      this.userInfo = {
        ...this.userInfo,
        province: this.selectedProvince
      }
      uni.setStorageSync(PROVINCE_STORAGE_KEY, this.selectedProvince)
    },

    async savePreferences(preferences) {
      this.preferences = normalizePreferences(preferences)
      uni.setStorageSync(PREFERENCES_STORAGE_KEY, JSON.stringify(this.preferences))
      try {
        await updatePreferences(this.preferences)
      } catch {
        return this.preferences
      }
      return this.preferences
    }
  }
})
