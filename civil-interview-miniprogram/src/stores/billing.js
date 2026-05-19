import { defineStore } from 'pinia'
import { BILLING_STORAGE_KEY } from '../utils/constants'

const PLANS = {
  trial: {
    key: 'trial',
    title: '试用版',
    status: '可体验 1 道引导题，熟悉录音/录像评分流程'
  },
  hourly: {
    key: 'hourly',
    title: '按时套餐',
    status: '3 小时训练时长，解锁全真模拟、定向备面和专项训练'
  },
  monthly: {
    key: 'monthly',
    title: '包月套餐',
    status: '30 天有效期，每日 1 小时训练额度'
  }
}

function isPaidPlanType(planType) {
  return planType === 'hourly' || planType === 'monthly'
}

function createDefaultState() {
  return {
    planType: 'trial',
    activatedAt: 0,
    isPaid: false,
    planName: '',
    status: '',
    remainingSeconds: 0,
    remainingMinutes: 0,
    remainingDailyMinutes: 0,
    dailyLimitMinutes: 0,
    usedMinutes: 0,
    totalMinutes: 0,
    monthlyExpireAt: 0,
    orderHistory: []
  }
}

function normalizeState(raw = {}) {
  const state = {
    ...createDefaultState(),
    ...(raw && typeof raw === 'object' ? raw : {})
  }
  const planType = String(state.planType || 'trial')
  state.planType = PLANS[planType] ? planType : 'trial'
  state.isPaid = state.isPaid === true || isPaidPlanType(state.planType)
  state.activatedAt = Number(state.activatedAt || 0)
  state.remainingSeconds = Math.max(0, Number(state.remainingSeconds || 0))
  state.remainingMinutes = Math.max(0, Number(state.remainingMinutes || 0))
  state.remainingDailyMinutes = Math.max(0, Number(state.remainingDailyMinutes || 0))
  state.dailyLimitMinutes = Math.max(0, Number(state.dailyLimitMinutes || 0))
  state.usedMinutes = Math.max(0, Number(state.usedMinutes || 0))
  state.totalMinutes = Math.max(0, Number(state.totalMinutes || 0))
  state.monthlyExpireAt = Math.max(0, Number(state.monthlyExpireAt || 0))
  state.orderHistory = Array.isArray(state.orderHistory) ? state.orderHistory : []
  return state
}

function loadState() {
  try {
    const raw = uni.getStorageSync(BILLING_STORAGE_KEY)
    return normalizeState(raw ? JSON.parse(raw) : {})
  } catch {
    return createDefaultState()
  }
}

export const useBillingStore = defineStore('billing', {
  state: () => loadState(),

  getters: {
    plan(state) {
      if (state.isPaid && state.planType === 'trial') {
        return {
          key: 'paid',
          title: state.planName || '已开通',
          status: '已解锁完整训练模块'
        }
      }
      return PLANS[state.planType] || PLANS.trial
    }
  },

  actions: {
    activate(planType) {
      this.planType = planType
      this.activatedAt = Date.now()
      this.isPaid = planType === 'hourly' || planType === 'monthly'
      this.planName = PLANS[planType]?.title || ''
      this.status = this.isPaid ? 'active' : 'trial'
      uni.setStorageSync(BILLING_STORAGE_KEY, JSON.stringify(this.$state))
    },

    applyBackendState(rawBilling = {}, permissions = {}) {
      const billing = rawBilling && typeof rawBilling === 'object' ? rawBilling : {}
      const planType = String(billing.planType || this.planType || 'trial')
      const hasPremiumPermission = !!permissions?.canAccessPremiumModules
      const backendPaid = billing.isPaid === true || hasPremiumPermission

      this.planType = PLANS[planType] ? planType : 'trial'
      this.activatedAt = Number(billing.activatedAt || this.activatedAt || 0)
      this.isPaid = backendPaid
      this.planName = String(billing.planName || PLANS[this.planType]?.title || '')
      this.status = String(billing.status || '')
      this.remainingSeconds = Math.max(0, Number(billing.remainingSeconds || 0))
      this.remainingMinutes = Math.max(0, Number(billing.remainingMinutes || Math.ceil(this.remainingSeconds / 60) || 0))
      this.remainingDailyMinutes = Math.max(0, Number(billing.remainingDailyMinutes || 0))
      this.dailyLimitMinutes = Math.max(0, Number(billing.dailyLimitMinutes || 0))
      this.usedMinutes = Math.max(0, Number(billing.usedMinutes || 0))
      this.totalMinutes = Math.max(0, Number(billing.totalMinutes || 0))
      this.monthlyExpireAt = Math.max(0, Number(billing.monthlyExpireAt || 0))
      this.orderHistory = Array.isArray(billing.orderHistory) ? billing.orderHistory : this.orderHistory || []
      uni.setStorageSync(BILLING_STORAGE_KEY, JSON.stringify(this.$state))
    },

    reset() {
      this.planType = 'trial'
      this.activatedAt = 0
      this.isPaid = false
      this.planName = ''
      this.status = ''
      this.remainingSeconds = 0
      this.remainingMinutes = 0
      this.remainingDailyMinutes = 0
      this.dailyLimitMinutes = 0
      this.usedMinutes = 0
      this.totalMinutes = 0
      this.monthlyExpireAt = 0
      this.orderHistory = []
      uni.setStorageSync(BILLING_STORAGE_KEY, JSON.stringify(this.$state))
    }
  }
})
