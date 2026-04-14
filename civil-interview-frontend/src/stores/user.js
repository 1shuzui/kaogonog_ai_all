import { defineStore } from 'pinia'
import { getUserInfo, updatePreferences, updateUserProfile, getProvinces } from '@/api/user'
import { login as loginApi, register as registerApi } from '@/api/auth'

const PREFERENCES_STORAGE_KEY = 'civil_user_preferences'
const PROVINCE_STORAGE_KEY = 'civil_selected_province'
const TOKEN_STORAGE_KEY = 'token'
const USERNAME_STORAGE_KEY = 'username'
const GUEST_STORAGE_SCOPE = 'guest'

const DEFAULT_PREFERENCES = {
  defaultPrepTime: 90,
  defaultAnswerTime: 180,
  enableVideo: true
}

function normalizePreferences(preferences) {
  const merged = {
    ...DEFAULT_PREFERENCES,
    ...(preferences || {})
  }
  const prep = Number(merged.defaultPrepTime)
  const answer = Number(merged.defaultAnswerTime)
  return {
    defaultPrepTime: Number.isFinite(prep) && prep > 0 ? prep : DEFAULT_PREFERENCES.defaultPrepTime,
    defaultAnswerTime: Number.isFinite(answer) && answer > 0 ? answer : DEFAULT_PREFERENCES.defaultAnswerTime,
    enableVideo: typeof merged.enableVideo === 'boolean' ? merged.enableVideo : DEFAULT_PREFERENCES.enableVideo
  }
}

function loadPreferencesFromStorage() {
  return loadPreferencesForUser()
}

function getStoredUsername() {
  try {
    return localStorage.getItem(USERNAME_STORAGE_KEY) || ''
  } catch {
    return ''
  }
}

function getStorageScope(username = '') {
  const scope = String(username || getStoredUsername() || GUEST_STORAGE_SCOPE).trim()
  return scope || GUEST_STORAGE_SCOPE
}

function buildScopedStorageKey(key, username = '') {
  return `${key}:${getStorageScope(username)}`
}

function loadPreferencesForUser(username = '') {
  try {
    const scopedKey = buildScopedStorageKey(PREFERENCES_STORAGE_KEY, username)
    const raw = localStorage.getItem(scopedKey) || localStorage.getItem(PREFERENCES_STORAGE_KEY)
    return raw ? normalizePreferences(JSON.parse(raw)) : { ...DEFAULT_PREFERENCES }
  } catch {
    return { ...DEFAULT_PREFERENCES }
  }
}

function savePreferencesToStorage(preferences, username = '') {
  try {
    localStorage.setItem(
      buildScopedStorageKey(PREFERENCES_STORAGE_KEY, username),
      JSON.stringify(normalizePreferences(preferences))
    )
  } catch {
    // ignore local storage failures
  }
}

function loadProvinceFromStorage() {
  return loadProvinceForUser()
}

function loadProvinceForUser(username = '') {
  try {
    return localStorage.getItem(buildScopedStorageKey(PROVINCE_STORAGE_KEY, username))
      || localStorage.getItem(PROVINCE_STORAGE_KEY)
      || 'national'
  } catch {
    return 'national'
  }
}

function saveProvinceToStorage(code, username = '') {
  try {
    localStorage.setItem(buildScopedStorageKey(PROVINCE_STORAGE_KEY, username), code || 'national')
  } catch {
    // ignore local storage failures
  }
}

export const useUserStore = defineStore('user', {
  state: () => ({
    token: localStorage.getItem('token') || '',
    username: localStorage.getItem('username') || '',
    email: '',
    userInfo: { id: '', name: '', avatar: '', province: 'national' },
    selectedProvince: loadProvinceFromStorage(),
    provinces: [],
    preferences: loadPreferencesFromStorage()
  }),

  getters: {
    isAuthenticated(state) {
      return !!state.token
    },
    provinceName(state) {
      const p = state.provinces.find(p => p.code === state.selectedProvince)
      return p ? p.name : '国考'
    }
  },

  actions: {
    async login(username, password) {
      const res = await loginApi(username, password)
      this.token = res.access_token
      this.username = username
      localStorage.setItem(TOKEN_STORAGE_KEY, res.access_token)
      localStorage.setItem(USERNAME_STORAGE_KEY, username)
      this.selectedProvince = loadProvinceForUser(username)
      this.preferences = loadPreferencesForUser(username)
      try {
        await this.loadUserInfo()
      } catch (error) {
        if (error?.response?.status === 401) {
          this.logout()
          throw error
        }
      }
      const { useExamStore } = await import('@/stores/exam')
      useExamStore().restorePersistedSession(username)
      return res
    },
    logout() {
      this.token = ''
      this.username = ''
      this.email = ''
      this.userInfo = { id: '', name: '', avatar: '', province: 'national' }
      localStorage.removeItem(TOKEN_STORAGE_KEY)
      localStorage.removeItem(USERNAME_STORAGE_KEY)
      this.selectedProvince = loadProvinceForUser()
      this.preferences = loadPreferencesForUser()
    },
    async register(form) {
      return registerApi(form)
    },
    async loadUserInfo() {
      const info = await getUserInfo()
      const activeUsername = info?.id || this.username
      if (activeUsername && activeUsername !== this.username) {
        this.username = activeUsername
        localStorage.setItem(USERNAME_STORAGE_KEY, activeUsername)
      }
      this.userInfo = {
        id: activeUsername,
        name: info?.name || activeUsername,
        avatar: info?.avatar || '',
        province: info?.province || 'national'
      }
      this.email = info?.email || ''
      this.selectedProvince = this.userInfo.province
      this.preferences = normalizePreferences(info?.preferences)
      saveProvinceToStorage(this.selectedProvince, activeUsername)
      savePreferencesToStorage(this.preferences, activeUsername)
      return this.userInfo
    },
    async loadProvinces() {
      this.provinces = await getProvinces()
    },
    setProvince(code) {
      this.selectedProvince = code
      saveProvinceToStorage(this.selectedProvince, this.username)
      this.userInfo = {
        ...this.userInfo,
        province: code || 'national'
      }
    },
    async persistProvince(code) {
      const previous = this.selectedProvince
      this.setProvince(code)
      if (!this.isAuthenticated) return { success: true }
      try {
        return await updateUserProfile({ province: this.selectedProvince })
      } catch (error) {
        this.setProvince(previous)
        return { success: false, error }
      }
    },
    async savePreferences(prefs) {
      this.preferences = normalizePreferences({
        ...this.preferences,
        ...(prefs || {})
      })
      savePreferencesToStorage(this.preferences, this.username)
      saveProvinceToStorage(this.selectedProvince, this.username)
      await updatePreferences(this.preferences)
      await updateUserProfile({ province: this.selectedProvince || 'national' })
      this.userInfo = {
        ...this.userInfo,
        province: this.selectedProvince || 'national'
      }
      await this.loadUserInfo()
    }
  }
})
