import { defineStore } from 'pinia'
import { BILLING_STORAGE_KEY } from '../utils/constants'

const PLANS = {
  trial: {
    key: 'trial',
    title: '试用版',
    status: '可体验 1 道引导题'
  },
  hourly: {
    key: 'hourly',
    title: '按时套餐',
    status: '已解锁完整训练模块'
  },
  monthly: {
    key: 'monthly',
    title: '包月套餐',
    status: '当前周期内可使用全部功能'
  }
}

function loadState() {
  try {
    const raw = uni.getStorageSync(BILLING_STORAGE_KEY)
    return raw ? JSON.parse(raw) : { planType: 'trial', activatedAt: 0 }
  } catch {
    return { planType: 'trial', activatedAt: 0 }
  }
}

export const useBillingStore = defineStore('billing', {
  state: () => loadState(),

  getters: {
    plan(state) {
      return PLANS[state.planType] || PLANS.trial
    },
    isPaid(state) {
      return state.planType === 'hourly' || state.planType === 'monthly'
    }
  },

  actions: {
    activate(planType) {
      this.planType = planType
      this.activatedAt = Date.now()
      uni.setStorageSync(BILLING_STORAGE_KEY, JSON.stringify(this.$state))
    },

    reset() {
      this.planType = 'trial'
      this.activatedAt = 0
      uni.setStorageSync(BILLING_STORAGE_KEY, JSON.stringify(this.$state))
    }
  }
})
