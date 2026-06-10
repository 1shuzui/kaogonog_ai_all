/**
 * 小程序权益状态仓库，保存当前套餐、剩余总分钟、每日剩余分钟、试用状态和权益刷新时间。
 *
 * 练习、定向、试用和支付页面都依赖这里判断可用性。实际扣量在后端完成，store 只展示后端返回的快照，
 * 防止端侧时间或本地缓存影响真实权益余额。
 *
 * @param 无；actions 接收刷新请求、权益切换请求或访问校验场景。
 * @return 导出 Pinia store，供首页、套餐中心、准备页和个人中心读取权益状态。
 * @raises Error: 未登录、接口失败或权益不可用时由 action 抛给页面处理。
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
