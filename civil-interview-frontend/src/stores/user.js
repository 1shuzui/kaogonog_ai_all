/**
 * 这个状态仓库保存 `user` 相关跨页面状态；把它放在 Pinia 里，是为了切页面后仍能复用同一份数据。
 *
 * @param 无；文件级模块依赖导出函数、组合式 API 或调用方传入上下文。
 * @return 导出可复用的端侧能力，具体返回值由各公共函数保持兼容。
 * @raises 不主动吞掉业务异常；请求失败、权限不足和运行时错误交由调用方或全局拦截器处理。
 */
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
  enableVideo: true,
  preferredQuestionDimensions: [],
  practicePreferenceConfirmed: false,
  examCategory: ''
}

const VALID_PREFERRED_QUESTION_DIMENSIONS = new Set([
  'analysis',
  'practical',
  'emergency',
  'logic',
  'expression',
  'legal'
])

function normalizeProvinceCode(code = '') {
  const normalized = String(code || '').trim()
  if (!normalized) return 'national'
  return normalized === 'shaanxi' ? 'shanxi' : normalized
}

function normalizePreferences(preferences) {
  const merged = {
    ...DEFAULT_PREFERENCES,
    ...(preferences || {})
  }
  const prep = Number(merged.defaultPrepTime)
  const answer = Number(merged.defaultAnswerTime)
  const rawDimensions = Array.isArray(merged.preferredQuestionDimensions)
    ? merged.preferredQuestionDimensions
    : typeof merged.preferredQuestionDimensions === 'string'
      ? merged.preferredQuestionDimensions.split(',')
      : []
  const preferredQuestionDimensions = rawDimensions
    .map((item) => String(item || '').trim())
    .filter((item, index, list) => VALID_PREFERRED_QUESTION_DIMENSIONS.has(item) && list.indexOf(item) === index)

  return {
    defaultPrepTime: Number.isFinite(prep) && prep > 0 ? prep : DEFAULT_PREFERENCES.defaultPrepTime,
    defaultAnswerTime: Number.isFinite(answer) && answer > 0 ? answer : DEFAULT_PREFERENCES.defaultAnswerTime,
    enableVideo: typeof merged.enableVideo === 'boolean' ? merged.enableVideo : DEFAULT_PREFERENCES.enableVideo,
    preferredQuestionDimensions,
    practicePreferenceConfirmed: merged.practicePreferenceConfirmed === true,
    examCategory: String(merged.examCategory || '').trim()
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
    return normalizeProvinceCode(localStorage.getItem(buildScopedStorageKey(PROVINCE_STORAGE_KEY, username))
      || localStorage.getItem(PROVINCE_STORAGE_KEY)
      || 'national')
  } catch {
    return 'national'
  }
}

function saveProvinceToStorage(code, username = '') {
  try {
    localStorage.setItem(
      buildScopedStorageKey(PROVINCE_STORAGE_KEY, username),
      normalizeProvinceCode(code)
    )
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

function isExplicitProvince(code = '') {
  const normalized = normalizeProvinceCode(code)
  return !!normalized && normalized !== 'national'
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
      terms: {
        hasAgreed: false,
        agreedVersion: '',
        latestVersion: '',
        updatedAt: '',
        effectiveAt: '',
        agreedAt: '',
        needsUpdate: false
      },
      permissions: {
        canManageQuestionBank: false,
        canAccessPremiumModules: false
      },
      accountBindings: {
        wechatMiniBound: false,
        wechatUnionBound: false,
        wechatWebBound: false
      },
      accountLogin: {
        requiresPcAccountSetup: false,
        pcLoginUsername: '',
        wechatGeneratedUsername: ''
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
      return !!state.userInfo?.isAdmin
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
        terms: {
          hasAgreed: false,
          agreedVersion: '',
          latestVersion: '',
          updatedAt: '',
          effectiveAt: '',
          agreedAt: '',
          needsUpdate: false
        },
        permissions: {
          canManageQuestionBank: false,
          canAccessPremiumModules: false
        },
        accountBindings: {
          wechatMiniBound: false,
          wechatUnionBound: false,
          wechatWebBound: false
        },
        accountLogin: {
          requiresPcAccountSetup: false,
          pcLoginUsername: '',
          wechatGeneratedUsername: ''
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
      const isAdmin = !!info?.isAdmin

      if (activeUsername && activeUsername !== this.username) {
        this.username = activeUsername
        localStorage.setItem(USERNAME_STORAGE_KEY, activeUsername)
      }

      this.userInfo = {
        id: activeUsername,
        name: info?.name || activeUsername,
        avatar: info?.avatar || '',
        province: normalizeProvinceCode(info?.province || 'national'),
        role: info?.role || 'user',
        isAdmin,
        billing: info?.billing || {},
        terms: info?.terms || {
          hasAgreed: false,
          agreedVersion: '',
          latestVersion: '',
          updatedAt: '',
          effectiveAt: '',
          agreedAt: '',
          needsUpdate: false
        },
        permissions: {
          canManageQuestionBank: isAdmin || !!info?.permissions?.canManageQuestionBank,
          canAccessPremiumModules: isAdmin || !!info?.permissions?.canAccessPremiumModules
        },
        accountBindings: {
          wechatMiniBound: info?.accountBindings?.wechatMiniBound === true,
          wechatUnionBound: info?.accountBindings?.wechatUnionBound === true,
          wechatWebBound: info?.accountBindings?.wechatWebBound === true
        },
        accountLogin: {
          requiresPcAccountSetup: info?.accountLogin?.requiresPcAccountSetup === true,
          pcLoginUsername: info?.accountLogin?.pcLoginUsername || '',
          wechatGeneratedUsername: info?.accountLogin?.wechatGeneratedUsername || ''
        }
      }
      this.email = info?.email || ''
      const backendProvince = normalizeProvinceCode(this.userInfo.province || '')
      const backendProvinceIsExplicit = isExplicitProvince(backendProvince)
      this.selectedProvince = backendProvince || loadProvinceForUser(activeUsername)
      this.provinceConfirmed = loadProvinceConfirmedForUser(activeUsername) || backendProvinceIsExplicit
      this.preferences = normalizePreferences({
        ...loadPreferencesForUser(activeUsername),
        ...(info?.preferences || {})
      })

      saveProvinceToStorage(this.selectedProvince, activeUsername)
      if (this.provinceConfirmed) {
        saveProvinceConfirmedToStorage(true, activeUsername)
      }
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
      this.selectedProvince = normalizeProvinceCode(code)
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

    requireProvinceSelection(resetProvince = false) {
      this.provinceConfirmed = false
      saveProvinceConfirmedToStorage(false, this.username)

      if (resetProvince) {
        this.setProvince('national')
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
