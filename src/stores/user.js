import { defineStore } from 'pinia'
import { getUserInfo, updatePreferences, updateUserProfile, getProvinces } from '@/api/user'
import { login as loginApi, register as registerApi } from '@/api/auth'
import { useBillingStore } from '@/stores/billing'

const PREFERENCES_STORAGE_KEY = 'civil_user_preferences'
const PROVINCE_STORAGE_KEY = 'civil_selected_province'
const PROVINCE_CONFIRMED_STORAGE_KEY = 'civil_selected_province_confirmed'
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

function loadProvinceConfirmedForUser(username = '') {
  try {
    const scopedKey = buildScopedStorageKey(PROVINCE_CONFIRMED_STORAGE_KEY, username)
    const raw = localStorage.getItem(scopedKey) ?? localStorage.getItem(PROVINCE_CONFIRMED_STORAGE_KEY)
    return raw === '1' || raw === 'true'
  } catch {
    return false
  }
}

function saveProvinceConfirmedToStorage(confirmed, username = '') {
  try {
    localStorage.setItem(
      buildScopedStorageKey(PROVINCE_CONFIRMED_STORAGE_KEY, username),
      confirmed ? '1' : '0'
    )
  } catch {
    // ignore local storage failures
  }
}

export const useUserStore = defineStore('user', {
  state: () => ({
    token: localStorage.getItem(TOKEN_STORAGE_KEY) || '',
    username: localStorage.getItem(USERNAME_STORAGE_KEY) || '',
    email: '',
    userInfo: {
      id: '',
      name: '',
      avatar: '',
      province: 'national',
      role: 'user',
      isAdmin: false,
      permissions: {
        canManageQuestionBank: false,
        canAccessPremiumModules: false
      }
    },
    selectedProvince: loadProvinceForUser(),
    provinceConfirmed: loadProvinceConfirmedForUser(),
    provinces: [],
    preferences: loadPreferencesForUser()
  }),

  getters: {
    isAuthenticated(state) {
      return !!state.token
    },
    isAdmin(state) {
      return !!state.userInfo?.isAdmin || state.username === 'admin' || state.userInfo?.id === 'admin'
    },
    roleLabel() {
      return this.isAdmin ? 'Admin' : 'User'
    },
    provinceName(state) {
      const province = state.provinces.find((item) => item.code === state.selectedProvince)
      return province ? province.name : '国考'
    },
    hasConfirmedProvinceSelection(state) {
      return !!state.provinceConfirmed
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
      this.provinceConfirmed = loadProvinceConfirmedForUser(username)
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
      this.userInfo = {
        id: '',
        name: '',
        avatar: '',
        province: 'national',
        role: 'user',
        isAdmin: false,
        permissions: {
          canManageQuestionBank: false,
          canAccessPremiumModules: false
        }
      }
      localStorage.removeItem(TOKEN_STORAGE_KEY)
      localStorage.removeItem(USERNAME_STORAGE_KEY)
      this.selectedProvince = loadProvinceForUser()
      this.provinceConfirmed = loadProvinceConfirmedForUser()
      this.preferences = loadPreferencesForUser()
      billingStore.resetToTrial()
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
        province: info?.province || 'national',
        role: info?.role || 'user',
        isAdmin: !!info?.isAdmin || activeUsername === 'admin',
        permissions: {
          canManageQuestionBank: !!info?.permissions?.canManageQuestionBank,
          canAccessPremiumModules: !!info?.permissions?.canAccessPremiumModules
        }
      }
      this.email = info?.email || ''
      this.selectedProvince = this.userInfo.province || loadProvinceForUser(activeUsername)
      this.provinceConfirmed = loadProvinceConfirmedForUser(activeUsername)
      this.preferences = normalizePreferences({
        ...loadPreferencesForUser(activeUsername),
        ...(info?.preferences || {})
      })

      saveProvinceToStorage(this.selectedProvince, activeUsername)
      savePreferencesToStorage(this.preferences, activeUsername)

      if (info?.billing) {
        billingStore.applyBackendState(info.billing)
      }

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

    async confirmProvinceSelection(code) {
      const previousProvince = this.selectedProvince
      const previousConfirmed = this.provinceConfirmed

      this.setProvince(code)
      this.provinceConfirmed = true
      saveProvinceConfirmedToStorage(true, this.username)

      if (!this.isAuthenticated) {
        return { success: true }
      }

      try {
        await updateUserProfile({ province: this.selectedProvince })
        this.userInfo = {
          ...this.userInfo,
          province: this.selectedProvince
        }
        return { success: true }
      } catch (error) {
        this.setProvince(previousProvince)
        this.provinceConfirmed = previousConfirmed
        saveProvinceConfirmedToStorage(previousConfirmed, this.username)
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
