import { defineStore } from 'pinia'
import { getUserInfo, updatePreferences, updateUserProfile, getProvinces } from '@/api/user'
import { login as loginApi, register as registerApi } from '@/api/auth'
import { useBillingStore } from '@/stores/billing'

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
    token: localStorage.getItem(TOKEN_STORAGE_KEY) || '',
    username: localStorage.getItem(USERNAME_STORAGE_KEY) || '',
    email: '',
    role: 'user',
    permissions: {
      canManageQuestionBank: false,
      canAccessPremiumModules: false
    },
    userInfo: { id: '', name: '', avatar: '', province: 'national' },
    selectedProvince: loadProvinceForUser(),
    provinces: [],
    preferences: loadPreferencesForUser()
  }),

  getters: {
    isAuthenticated(state) {
      return !!state.token
    },
    isAdmin(state) {
      return state.role === 'admin' || state.username === 'admin' || state.userInfo?.id === 'admin'
    },
    roleLabel() {
      return this.isAdmin ? '管理员' : '普通用户'
    },
    provinceName(state) {
      const province = state.provinces.find((item) => item.code === state.selectedProvince)
      return province ? province.name : 'National'
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
        }
        throw error
      }

      return res
    },

    logout() {
      const billingStore = useBillingStore()
      this.token = ''
      this.username = ''
      this.email = ''
      this.role = 'user'
      this.permissions = {
        canManageQuestionBank: false,
        canAccessPremiumModules: false
      }
      this.userInfo = { id: '', name: '', avatar: '', province: 'national' }
      localStorage.removeItem(TOKEN_STORAGE_KEY)
      localStorage.removeItem(USERNAME_STORAGE_KEY)
      this.selectedProvince = loadProvinceForUser()
      this.preferences = loadPreferencesForUser()
      billingStore.resetLocalState()
    },

    async register(form) {
      return registerApi(form)
    },

    async loadUserInfo() {
      const billingStore = useBillingStore()
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
      this.role = info?.role || (activeUsername === 'admin' ? 'admin' : 'user')
      this.permissions = {
        canManageQuestionBank: !!info?.permissions?.canManageQuestionBank,
        canAccessPremiumModules: !!info?.permissions?.canAccessPremiumModules
      }
      this.selectedProvince = this.userInfo.province || loadProvinceForUser(activeUsername)
      this.preferences = normalizePreferences({
        ...loadPreferencesForUser(activeUsername),
        ...(info?.preferences || {})
      })

      billingStore.applyServerBilling(info?.billing || {}, activeUsername)
      saveProvinceToStorage(this.selectedProvince, activeUsername)
      savePreferencesToStorage(this.preferences, activeUsername)

      return this.userInfo
    },

    async loadProvinces() {
      this.provinces = await getProvinces()
    },

    setProvince(code) {
      this.selectedProvince = code || 'national'
      saveProvinceToStorage(this.selectedProvince, this.username)
      this.userInfo = {
        ...this.userInfo,
        province: this.selectedProvince
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
