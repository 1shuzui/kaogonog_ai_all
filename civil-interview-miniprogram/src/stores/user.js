import { defineStore } from 'pinia'
import { bindWechatMiniProgram, login as loginApi, loginWithWechat as loginWithWechatApi, register as registerApi, setupWechatMiniProgramAccount } from '../api/auth'
import { getProvinces, getUserInfo, updatePreferences, updateUserProfile } from '../api/user'
import { useBillingStore } from './billing'
import {
  DEFAULT_PREFERENCES,
  PREFERENCES_STORAGE_KEY,
  PROVINCE_STORAGE_KEY,
  QUESTION_CATEGORIES,
  PROVINCES,
  TOKEN_STORAGE_KEY,
  USERNAME_STORAGE_KEY
} from '../utils/constants'
import { logger } from '../utils/logger'

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

function safeSetStorage(key, value) {
  try {
    uni.setStorageSync(key, value)
  } catch (error) {
    logger.warn('Local storage write failed', {
      event: 'mini.storage.write_failed',
      key,
      error
    })
  }
}

function normalizeProvinceCode(code = '') {
  const normalized = String(code || '').trim()
  if (!normalized) return 'national'
  return normalized === 'shaanxi' ? 'shanxi' : normalized
}

function normalizePreferences(preferences = {}) {
  const merged = {
    ...DEFAULT_PREFERENCES,
    ...(preferences || {})
  }
  const validQuestionDimensions = new Set(QUESTION_CATEGORIES.map((item) => item.key).filter(Boolean))
  const preferredQuestionDimensions = Array.isArray(merged.preferredQuestionDimensions)
    ? merged.preferredQuestionDimensions
      .map((item) => String(item || '').trim())
      .filter((item, index, list) => validQuestionDimensions.has(item) && list.indexOf(item) === index)
    : []
  return {
    defaultPrepTime: Math.max(30, Number(merged.defaultPrepTime) || DEFAULT_PREFERENCES.defaultPrepTime),
    defaultAnswerTime: Math.max(60, Number(merged.defaultAnswerTime) || DEFAULT_PREFERENCES.defaultAnswerTime),
    enableAudio: merged.enableAudio !== false && merged.enableVideo !== false,
    preferredQuestionDimensions,
    practicePreferenceConfirmed: merged.practicePreferenceConfirmed === true
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
      province: normalizeProvinceCode(readStorage(PROVINCE_STORAGE_KEY, 'national')),
      role: 'user',
      isAdmin: false,
      billing: {
        planType: 'trial',
        isPaid: false
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
    selectedProvince: normalizeProvinceCode(readStorage(PROVINCE_STORAGE_KEY, 'national')),
    provinces: PROVINCES,
    preferences: normalizePreferences(readJsonStorage(PREFERENCES_STORAGE_KEY, DEFAULT_PREFERENCES))
  }),

  getters: {
    isAuthenticated(state) {
      return !!state.token
    },
    isAdmin(state) {
      return !!state.userInfo?.isAdmin
    },
    displayName(state) {
      const baseName = state.userInfo?.name || state.username || '考生'
      const isAdmin = !!state.userInfo?.isAdmin
      return isAdmin ? `${baseName}（管理员权限）` : baseName
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

    async loginWithWechat(code, agreedTermsVersion) {
      const response = await loginWithWechatApi(code, agreedTermsVersion)
      this.token = response.access_token
      this.username = response.username || ''
      uni.setStorageSync(TOKEN_STORAGE_KEY, response.access_token)
      if (response.username) uni.setStorageSync(USERNAME_STORAGE_KEY, response.username)
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
        isAdmin: false,
        billing: {
          planType: 'trial',
          isPaid: false
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
      uni.removeStorageSync(TOKEN_STORAGE_KEY)
      uni.removeStorageSync(USERNAME_STORAGE_KEY)
    },

    async loadUserInfo() {
      const billingStore = useBillingStore()
      const info = await getUserInfo({ skipErrorHandler: true })
      const username = info?.id || this.username
      const isAdmin = !!info?.isAdmin
      const permissions = {
        canManageQuestionBank: isAdmin || !!info?.permissions?.canManageQuestionBank,
        canAccessPremiumModules: isAdmin || !!info?.permissions?.canAccessPremiumModules
      }
      const billing = {
        planType: info?.billing?.planType || 'trial',
        remainingSeconds: Number(info?.billing?.remainingSeconds || 0),
        remainingMinutes: Number(info?.billing?.remainingMinutes || 0),
        remainingDailyMinutes: Number(info?.billing?.remainingDailyMinutes || 0),
        dailyLimitMinutes: Number(info?.billing?.dailyLimitMinutes || 0),
        usedMinutes: Number(info?.billing?.usedMinutes || 0),
        totalMinutes: Number(info?.billing?.totalMinutes || 0),
        monthlyExpireAt: Number(info?.billing?.monthlyExpireAt || 0),
        activatedAt: Number(info?.billing?.activatedAt || 0),
        orderHistory: Array.isArray(info?.billing?.orderHistory) ? info.billing.orderHistory : [],
        isPaid: isAdmin || permissions.canAccessPremiumModules || info?.billing?.isPaid === true
      }
      this.username = username
      if (username) safeSetStorage(USERNAME_STORAGE_KEY, username)

      this.userInfo = {
        id: username,
        name: info?.name || username || '考生',
        avatar: info?.avatar || '',
        province: normalizeProvinceCode(info?.province || this.selectedProvince || 'national'),
        role: info?.role || 'user',
        isAdmin,
        billing,
        permissions,
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
      try {
        billingStore.applyBackendState(billing, permissions)
      } catch (error) {
        logger.warn('Billing state sync failed', {
          event: 'mini.billing.sync_failed',
          username,
          error
        })
      }
      if (info?.province) {
        this.selectedProvince = normalizeProvinceCode(info.province)
        this.userInfo = {
          ...this.userInfo,
          province: this.selectedProvince
        }
        safeSetStorage(PROVINCE_STORAGE_KEY, this.selectedProvince)
      }
      if (info?.preferences) {
        this.preferences = normalizePreferences({
          ...this.preferences,
          ...info.preferences
        })
        safeSetStorage(PREFERENCES_STORAGE_KEY, JSON.stringify(this.preferences))
      }
      return this.userInfo
    },

    async bindWechat(code) {
      const response = await bindWechatMiniProgram(code)
      await this.loadUserInfo().catch(() => null)
      return response
    },

    async setupWechatPcAccount(data) {
      const response = await setupWechatMiniProgramAccount(data)
      if (response?.access_token) {
        this.token = response.access_token
        safeSetStorage(TOKEN_STORAGE_KEY, response.access_token)
      }
      if (response?.username) {
        this.username = response.username
        safeSetStorage(USERNAME_STORAGE_KEY, response.username)
      }
      await this.loadUserInfo().catch(() => null)
      return response
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
      this.selectedProvince = normalizeProvinceCode(code)
      this.userInfo = {
        ...this.userInfo,
        province: this.selectedProvince
      }
      safeSetStorage(PROVINCE_STORAGE_KEY, this.selectedProvince)
    },

    async savePreferences(preferences) {
      this.preferences = normalizePreferences(preferences)
      safeSetStorage(PREFERENCES_STORAGE_KEY, JSON.stringify(this.preferences))
      try {
        await updatePreferences(this.preferences)
        await updateUserProfile({ province: this.selectedProvince || 'national' })
      } catch {
        return this.preferences
      }
      return this.preferences
    }
  }
})
