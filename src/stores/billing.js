import { defineStore } from 'pinia'
import {
  BILLING_PLAN_KEYS,
  BILLING_ORDER_STATUS,
  HOURLY_PLAN_TOTAL_SECONDS,
  MONTHLY_PLAN_DURATION_MS,
  PREMIUM_MODULES,
  TRIAL_QUESTION,
  formatDurationText,
  formatPlanExpireAt,
  getPlanAmount,
  getPlanActivationSummary,
  getPlanTitle,
  isTrialEntryRoute,
  normalizeBillingCopy
} from '@/utils/billing'

const BILLING_STORAGE_KEY = 'civil_billing_state'

function createDefaultState() {
  return {
    planType: BILLING_PLAN_KEYS.TRIAL,
    remainingSeconds: 0,
    monthlyExpireAt: 0,
    activatedAt: 0,
    orderHistory: [],
    paywallVisible: false,
    paywallSource: '',
    activeSessionStartedAt: 0,
    activeSessionKind: '',
    lastPaywallSource: '',
    lastIntendedPath: ''
  }
}

function normalizeBillingState(rawState = {}) {
  const nextState = createDefaultState()
  const planType = String(rawState.planType || BILLING_PLAN_KEYS.TRIAL)

  return {
    ...nextState,
    ...rawState,
    planType: Object.values(BILLING_PLAN_KEYS).includes(planType) ? planType : BILLING_PLAN_KEYS.TRIAL,
    remainingSeconds: Math.max(0, Math.floor(Number(rawState.remainingSeconds) || 0)),
    monthlyExpireAt: Math.max(0, Number(rawState.monthlyExpireAt) || 0),
    activatedAt: Math.max(0, Number(rawState.activatedAt) || 0),
    orderHistory: Array.isArray(rawState.orderHistory)
      ? rawState.orderHistory
        .map((order) => ({
          id: String(order?.id || ''),
          planType: String(order?.planType || ''),
          title: getPlanTitle(String(order?.planType || '')) || normalizeBillingCopy(order?.title),
          amount: Number(order?.amount) || 0,
          status: String(order?.status || BILLING_ORDER_STATUS.PAID),
          summary: getPlanActivationSummary(String(order?.planType || '')) || normalizeBillingCopy(order?.summary),
          createdAt: Number(order?.createdAt) || 0
        }))
        .filter((order) => order.id)
      : [],
    paywallVisible: !!rawState.paywallVisible,
    paywallSource: normalizeBillingCopy(rawState.paywallSource),
    activeSessionStartedAt: Math.max(0, Number(rawState.activeSessionStartedAt) || 0),
    activeSessionKind: String(rawState.activeSessionKind || ''),
    lastPaywallSource: normalizeBillingCopy(rawState.lastPaywallSource),
    lastIntendedPath: String(rawState.lastIntendedPath || '')
  }
}

function loadBillingState() {
  try {
    const raw = localStorage.getItem(BILLING_STORAGE_KEY)
    if (!raw) return createDefaultState()
    return normalizeBillingState(JSON.parse(raw))
  } catch {
    return createDefaultState()
  }
}

function persistBillingState(state) {
  try {
    localStorage.setItem(BILLING_STORAGE_KEY, JSON.stringify(normalizeBillingState(state)))
  } catch {
    // ignore local storage failures
  }
}

export const useBillingStore = defineStore('billing', {
  state: () => loadBillingState(),

  getters: {
    isHourlyPlan(state) {
      return state.planType === BILLING_PLAN_KEYS.HOURLY
    },
    isMonthlyPlan(state) {
      return state.planType === BILLING_PLAN_KEYS.MONTHLY
    },
    isMonthlyActive() {
      return this.isMonthlyPlan && this.monthlyExpireAt > Date.now()
    },
    isHourlyActive() {
      return this.isHourlyPlan && this.remainingSeconds > 0
    },
    isPaid() {
      return this.isHourlyActive || this.isMonthlyActive
    },
    isTrialOnly() {
      return !this.isPaid
    },
    planLabel() {
      if (this.isMonthlyActive) return '包月套餐'
      if (this.isHourlyPlan) return '按时套餐'
      return '试用版'
    },
    planStatusText() {
      if (this.isMonthlyActive) {
        return `有效期至 ${formatPlanExpireAt(this.monthlyExpireAt)}`
      }
      if (this.isMonthlyPlan && !this.isMonthlyActive) {
        return '包月套餐已过期'
      }
      if (this.isHourlyPlan && this.remainingSeconds > 0) {
        return `剩余时长：${formatDurationText(this.remainingSeconds)}`
      }
      if (this.isHourlyPlan && this.remainingSeconds <= 0) {
        return '按时套餐时长已用完'
      }
      return '当前为试用模式，仅可体验 1 道引导题'
    },
    activePlanDescription() {
      if (this.isMonthlyActive) return '当前周期内已解锁全部付费训练模块'
      if (this.isHourlyPlan && this.remainingSeconds > 0) return '剩余时长内可使用全部付费训练模块'
      return '开通后可解锁完整训练功能'
    },
    unlockedModules() {
      return this.isPaid ? PREMIUM_MODULES : ['试用题']
    },
    recentOrders(state) {
      return [...state.orderHistory].sort((a, b) => b.createdAt - a.createdAt)
    },
    trialQuestion() {
      return { ...TRIAL_QUESTION }
    }
  },

  actions: {
    persist() {
      persistBillingState(this.$state)
    },

    applyBackendState(rawBillingState = {}) {
      const nextState = normalizeBillingState(rawBillingState)
      this.planType = nextState.planType
      this.remainingSeconds = nextState.remainingSeconds
      this.monthlyExpireAt = nextState.monthlyExpireAt
      this.activatedAt = nextState.activatedAt
      this.orderHistory = nextState.orderHistory
      this.persist()
    },

    syncPlanState() {
      if (this.isMonthlyPlan && this.monthlyExpireAt > 0 && this.monthlyExpireAt <= Date.now()) {
        this.planType = BILLING_PLAN_KEYS.TRIAL
        this.monthlyExpireAt = 0
      }
      if (this.isHourlyPlan && this.remainingSeconds <= 0) {
        this.remainingSeconds = 0
      }
      if (!this.isHourlyPlan && this.activeSessionStartedAt) {
        this.activeSessionStartedAt = 0
        this.activeSessionKind = ''
      }
      this.persist()
    },

    setPaywallIntent(path = '', source = '') {
      this.lastIntendedPath = String(path || '')
      this.lastPaywallSource = String(source || '')
      this.persist()
    },

    clearPaywallIntent() {
      this.lastIntendedPath = ''
      this.lastPaywallSource = ''
      this.persist()
    },

    openPaywall(path = '', source = '') {
      this.lastIntendedPath = String(path || '')
      this.lastPaywallSource = String(source || '')
      this.paywallSource = String(source || '')
      this.paywallVisible = true
      this.persist()
    },

    closePaywall() {
      this.paywallVisible = false
      this.paywallSource = ''
      this.persist()
    },

    canAccessRoute(routeLike = {}) {
      this.syncPlanState()
      if (!routeLike?.meta?.requiresPayment) return true
      if (routeLike?.name === 'ExamPrepare' && isTrialEntryRoute(routeLike)) return true
      return this.isPaid
    },

    createPaidOrder(planType, now = Date.now()) {
      const order = {
        id: `order_${now}_${Math.random().toString(36).slice(2, 8)}`,
        planType,
        title: getPlanTitle(planType),
        amount: getPlanAmount(planType),
        status: BILLING_ORDER_STATUS.PAID,
        summary: getPlanActivationSummary(planType),
        createdAt: now
      }
      this.orderHistory = [order, ...this.orderHistory].slice(0, 20)
      return order
    },

    activatePlan(planType) {
      const now = Date.now()
      let order = null

      if (planType === BILLING_PLAN_KEYS.HOURLY) {
        this.planType = BILLING_PLAN_KEYS.HOURLY
        this.remainingSeconds = HOURLY_PLAN_TOTAL_SECONDS
        this.monthlyExpireAt = 0
        order = this.createPaidOrder(planType, now)
      } else if (planType === BILLING_PLAN_KEYS.MONTHLY) {
        this.planType = BILLING_PLAN_KEYS.MONTHLY
        this.monthlyExpireAt = now + MONTHLY_PLAN_DURATION_MS
        this.remainingSeconds = 0
        order = this.createPaidOrder(planType, now)
      } else {
        this.planType = BILLING_PLAN_KEYS.TRIAL
        this.remainingSeconds = 0
        this.monthlyExpireAt = 0
      }

      this.activatedAt = now
      this.activeSessionStartedAt = 0
      this.activeSessionKind = ''
      this.persist()
      return order
    },

    resetToTrial() {
      this.$patch(createDefaultState())
      this.persist()
    },

    startUsageSession(kind = 'exam') {
      this.syncPlanState()
      if (!this.isHourlyActive || this.activeSessionStartedAt) return
      this.activeSessionStartedAt = Date.now()
      this.activeSessionKind = String(kind || 'exam')
      this.persist()
    },

    stopUsageSession() {
      if (!this.activeSessionStartedAt) return 0

      const sessionStart = Number(this.activeSessionStartedAt) || 0
      const before = this.remainingSeconds
      const consumedSeconds = Math.max(0, Math.ceil((Date.now() - sessionStart) / 1000))

      if (this.isHourlyPlan) {
        this.remainingSeconds = Math.max(0, this.remainingSeconds - consumedSeconds)
      }

      this.activeSessionStartedAt = 0
      this.activeSessionKind = ''
      this.syncPlanState()

      return Math.max(0, before - this.remainingSeconds)
    }
  }
})
