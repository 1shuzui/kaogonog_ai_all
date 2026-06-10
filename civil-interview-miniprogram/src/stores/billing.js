/**
 * 小程序账单状态仓库保存套餐展示用的本地快照，正式支付和权益到账必须以微信虚拟支付与后端订阅结果为准。
 *
 * 这里不能出现普通微信支付兜底，也不能在支付回调前本地授予训练时长；审核和售后都依赖服务端订单链路完整。
 * 本地缓存只让套餐中心和“我的”页在刷新前有可读状态，进入付费功能时仍要重新同步权益。
 *
 * @param 无；actions 接收套餐快照、支付订单摘要和服务端订阅状态。
 * @return 导出 Pinia store，供套餐中心、订单中心和权益提示组件复用。
 * @raises 不主动抛业务异常；接口失败由 action 或调用页面转成提示。
 */
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
    title: '3小时套餐',
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
  const source = raw && typeof raw === 'object' ? raw : {}
  const state = {
    ...createDefaultState(),
    ...source
  }
  const planType = String(state.planType || 'trial')
  state.planType = PLANS[planType] ? planType : 'trial'
  state.isPaid = state.isPaid === true || isPaidPlanType(state.planType)
  state.activatedAt = Number(state.activatedAt || 0)
  state.remainingSeconds = Math.max(0, Number(state.remainingSeconds || 0))
  state.remainingMinutes = Math.max(0, Number(state.remainingMinutes || 0))
  const hasDailyRemaining = source.remainingDailyMinutes !== undefined && source.remainingDailyMinutes !== null && source.remainingDailyMinutes !== ''
  state.remainingDailyMinutes = hasDailyRemaining ? Math.max(0, Number(state.remainingDailyMinutes || 0)) : state.remainingMinutes
  if (state.remainingMinutes > 0) {
    state.remainingDailyMinutes = Math.min(state.remainingDailyMinutes, state.remainingMinutes)
  }
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
      const hasDailyRemaining = billing.remainingDailyMinutes !== undefined && billing.remainingDailyMinutes !== null && billing.remainingDailyMinutes !== ''
      this.remainingDailyMinutes = hasDailyRemaining ? Math.max(0, Number(billing.remainingDailyMinutes || 0)) : this.remainingMinutes
      if (this.remainingMinutes > 0) {
        this.remainingDailyMinutes = Math.min(this.remainingDailyMinutes, this.remainingMinutes)
      }
      this.dailyLimitMinutes = Math.max(0, Number(billing.dailyLimitMinutes || 0))
      this.usedMinutes = Math.max(0, Number(billing.usedMinutes || 0))
      this.totalMinutes = Math.max(0, Number(billing.totalMinutes || 0))
      this.monthlyExpireAt = Math.max(0, Number(billing.monthlyExpireAt || 0))
      this.orderHistory = Array.isArray(billing.orderHistory) ? billing.orderHistory : this.orderHistory || []
      uni.setStorageSync(BILLING_STORAGE_KEY, JSON.stringify(this.$state))
    },

  }
})
