/**
 * 这个状态仓库保存 `subscription` 相关跨页面状态；把它放在 Pinia 里，是为了切页面后仍能复用同一份数据。
 *
 * @param 无；文件级模块依赖导出函数、组合式 API 或调用方传入上下文。
 * @return 导出可复用的端侧能力，具体返回值由各公共函数保持兼容。
 * @raises 不主动吞掉业务异常；请求失败、权限不足和运行时错误交由调用方或全局拦截器处理。
 */
import { defineStore } from 'pinia'
import { checkSubscriptionAccess, getSubscriptionStatus, switchSubscription } from '../api/subscription'
import { useBillingStore } from './billing'

function normalizeStatus(payload = {}) {
  const remainingMinutes = Math.max(0, Number(payload?.remainingMinutes || 0))
  const hasDailyRemaining = payload?.remainingDailyMinutes !== undefined && payload?.remainingDailyMinutes !== null && payload?.remainingDailyMinutes !== ''
  const rawRemainingDailyMinutes = hasDailyRemaining ? Number(payload.remainingDailyMinutes) : remainingMinutes
  const remainingDailyMinutes = remainingMinutes > 0 ? Math.min(Math.max(0, rawRemainingDailyMinutes || 0), remainingMinutes) : 0
  const activeSubscriptionId = Number(payload?.activeSubscriptionId || payload?.subscriptionId || payload?.id || 0)
  const entitlements = Array.isArray(payload?.entitlements)
    ? payload.entitlements.map((item) => normalizeEntitlement(item, activeSubscriptionId))
    : []
  return {
    id: activeSubscriptionId,
    subscriptionId: activeSubscriptionId,
    activeSubscriptionId,
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
    remainingMinutes,
    remainingDailyMinutes,
    expiresAt: payload?.expiresAt || '',
    canUse: payload?.canUse === true,
    packageCode: payload?.packageCode || '',
    stacked: payload?.stacked === true,
    activePlanCount: Number(payload?.activePlanCount || 0),
    entitlements
  }
}

function normalizeEntitlement(payload = {}, activeSubscriptionId = 0) {
  const subscriptionId = Number(payload?.subscriptionId || payload?.id || 0)
  const remainingMinutes = Math.max(0, Number(payload?.remainingMinutes || 0))
  const hasDailyRemaining = payload?.remainingDailyMinutes !== undefined && payload?.remainingDailyMinutes !== null && payload?.remainingDailyMinutes !== ''
  const rawRemainingDailyMinutes = hasDailyRemaining ? Number(payload.remainingDailyMinutes) : remainingMinutes
  return {
    id: subscriptionId,
    subscriptionId,
    isActiveSelection: payload?.isActiveSelection === true || (activeSubscriptionId > 0 && subscriptionId === activeSubscriptionId),
    planType: payload?.planType || 'trial',
    planName: payload?.planName || '',
    packageCode: payload?.packageCode || '',
    status: payload?.status || '',
    totalMinutes: Number(payload?.totalMinutes || 0),
    usedMinutes: Number(payload?.usedMinutes || 0),
    dailyLimitMinutes: Number(payload?.dailyLimitMinutes || 0),
    dailyUsedMinutes: Number(payload?.dailyUsedMinutes || 0),
    remainingMinutes,
    remainingDailyMinutes: remainingMinutes > 0 ? Math.min(Math.max(0, rawRemainingDailyMinutes || 0), remainingMinutes) : 0,
    expiresAt: payload?.expiresAt || '',
    canUse: payload?.canUse === true,
    sourceOrderNo: payload?.sourceOrderNo || '',
    startAt: payload?.startAt || ''
  }
}

function hasPremiumPlan(status = {}) {
  if (status.isTrialUser) return false
  if (!['hourly', 'monthly'].includes(status.planType)) return false
  return status.hasActivePlan === true || status.canUse === true
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
    hasPremiumAccess(state) {
      return hasPremiumPlan(state.status)
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
      const premium = hasPremiumPlan(this.status)
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
        isPaid: premium
      }, {
        canAccessPremiumModules: premium
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
    },

    async switchActive(subscriptionId, config = {}) {
      this.loading = true
      try {
        const payload = await switchSubscription(subscriptionId, config)
        return this.applyStatus(payload)
      } finally {
        this.loading = false
      }
    }
  }
})
