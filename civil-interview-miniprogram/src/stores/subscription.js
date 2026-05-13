import { defineStore } from 'pinia'
import { checkSubscriptionAccess, getSubscriptionStatus } from '../api/subscription'
import { useBillingStore } from './billing'

function normalizeStatus(payload = {}) {
  return {
    isTrialUser: payload?.isTrialUser !== false,
    trialCompleted: payload?.trialCompleted === true,
    hasActivePlan: payload?.hasActivePlan === true,
    planType: payload?.planType || 'trial',
    planName: payload?.planName || '',
    status: payload?.status || '',
    totalMinutes: Number(payload?.totalMinutes || 0),
    usedMinutes: Number(payload?.usedMinutes || 0),
    dailyLimitMinutes: Number(payload?.dailyLimitMinutes || 0),
    dailyUsedMinutes: Number(payload?.dailyUsedMinutes || 0),
    remainingMinutes: Number(payload?.remainingMinutes || 0),
    remainingDailyMinutes: Number(payload?.remainingDailyMinutes || 0),
    expiresAt: payload?.expiresAt || '',
    canUse: payload?.canUse === true,
    packageCode: payload?.packageCode || ''
  }
}

export const useSubscriptionStore = defineStore('subscription', {
  state: () => ({
    status: normalizeStatus(),
    access: null,
    loading: false
  }),

  getters: {
    isActive(state) {
      return state.status.hasActivePlan || state.status.canUse
    },
    remainingLabel(state) {
      const remaining = Math.max(0, Number(state.status.remainingMinutes || 0))
      const daily = Math.max(0, Number(state.status.remainingDailyMinutes || 0))
      if (state.status.dailyLimitMinutes > 0) return `${daily} / ${remaining} 分钟`
      return `${remaining} 分钟`
    }
  },

  actions: {
    applyStatus(payload = {}) {
      this.status = normalizeStatus(payload)
      const billingStore = useBillingStore()
      billingStore.applyBackendState({
        planType: this.status.planType,
        planName: this.status.planName,
        status: this.status.status,
        remainingSeconds: this.status.remainingMinutes * 60,
        remainingMinutes: this.status.remainingMinutes,
        remainingDailyMinutes: this.status.remainingDailyMinutes,
        dailyLimitMinutes: this.status.dailyLimitMinutes,
        usedMinutes: this.status.usedMinutes,
        totalMinutes: this.status.totalMinutes,
        monthlyExpireAt: this.status.expiresAt ? Date.parse(this.status.expiresAt) || 0 : 0,
        isPaid: this.status.hasActivePlan
      }, {
        canAccessPremiumModules: this.status.canUse || this.status.hasActivePlan
      })
      return this.status
    },

    async refresh(config = {}) {
      this.loading = true
      try {
        const payload = await getSubscriptionStatus(config)
        return this.applyStatus(payload)
      } finally {
        this.loading = false
      }
    },

    async check(mode = 'practice', config = {}) {
      this.access = await checkSubscriptionAccess(mode, config)
      return this.access
    }
  }
})
