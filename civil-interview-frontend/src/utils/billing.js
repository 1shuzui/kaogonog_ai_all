export const BILLING_PLAN_KEYS = {
  TRIAL: 'trial',
  HOURLY: 'hourly',
  MONTHLY: 'monthly'
}

export const BILLING_ORDER_STATUS = {
  PAID: 'paid'
}

export const HOURLY_PLAN_TOTAL_SECONDS = 3 * 60 * 60
export const MONTHLY_PLAN_DURATION_MS = 30 * 24 * 60 * 60 * 1000

export const PREMIUM_MODULES = [
  '完整模拟面试',
  '定向备考',
  '专项训练'
]

export const TRIAL_QUESTION = {
  id: 'q001',
  dimension: '综合分析',
  questionType: '结构化面试',
  sourceLabel: '试用题'
}

const BILLING_COPY_MAP = {
  'Full mock exam': '完整模拟面试',
  'Targeted preparation': '定向备考',
  'Dimension training': '专项训练',
  'Trial question': '试用题',
  'Premium module': '付费功能',
  'Free Trial': '免费试用',
  '3 Hours': '3小时体验包',
  '30 Days': '30天畅练卡',
  '3 Hours Plan': '3小时体验包',
  'Monthly Plan': '30天畅练卡',
  'Trial': '试用版',
  'Hourly': '按时套餐',
  'Monthly': '包月套餐',
  'Structured interview': '结构化面试',
  'analysis': '综合分析',
  'Hourly access activated in local demo mode': '已在本地演示模式下开通按时套餐',
  'Monthly access activated in local demo mode': '已在本地演示模式下开通包月套餐'
}

export const BILLING_PLANS = [
  {
    key: BILLING_PLAN_KEYS.TRIAL,
    badge: '试用',
    title: '免费试用',
    priceText: '¥0',
    description: '先体验 1 道引导题，完整走一遍面试流程后再决定是否开通。',
    features: [
      '可体验 1 道试用题',
      '可查看完整记录与结果流程',
      '适合首次熟悉系统'
    ]
  },
  {
    key: BILLING_PLAN_KEYS.HOURLY,
    badge: '按时',
    title: '3小时体验包',
    priceText: '¥99',
    description: '适合临近面试前的集中冲刺和短时高强度练习。',
    features: [
      '解锁全部付费训练模块',
      '按剩余时长计费体验',
      '适合短时冲刺练习'
    ]
  },
  {
    key: BILLING_PLAN_KEYS.MONTHLY,
    badge: '包月',
    title: '30天畅练卡',
    priceText: '¥1000',
    description: '适合系统化备考和连续多天的高频训练。',
    features: [
      '30天内不限次数使用',
      '适合稳定推进训练计划',
      '无需关注剩余小时数'
    ]
  }
]

export function formatDurationText(totalSeconds = 0) {
  const safeSeconds = Math.max(0, Math.floor(Number(totalSeconds) || 0))
  const hours = Math.floor(safeSeconds / 3600)
  const minutes = Math.floor((safeSeconds % 3600) / 60)

  if (hours > 0 && minutes > 0) return `${hours}小时${minutes}分钟`
  if (hours > 0) return `${hours}小时`
  if (minutes > 0) return `${minutes}分钟`
  if (safeSeconds > 0) return `${safeSeconds}秒`
  return '0分钟'
}

export function formatPlanExpireAt(timestamp) {
  const value = Number(timestamp)
  if (!Number.isFinite(value) || value <= 0) return ''
  const date = new Date(value)
  const year = date.getFullYear()
  const month = String(date.getMonth() + 1).padStart(2, '0')
  const day = String(date.getDate()).padStart(2, '0')
  return `${year}-${month}-${day}`
}

export function isTrialEntryRoute(routeLike = {}) {
  return String(routeLike?.query?.trial || '') === '1'
}

export function normalizeBillingCopy(value = '') {
  const text = String(value || '')
  return BILLING_COPY_MAP[text] || text
}

export function getPlanTitle(planType) {
  if (planType === BILLING_PLAN_KEYS.HOURLY) return '3小时体验包'
  if (planType === BILLING_PLAN_KEYS.MONTHLY) return '30天畅练卡'
  return '免费试用'
}

export function getPlanActivationSummary(planType) {
  if (planType === BILLING_PLAN_KEYS.HOURLY) return '已在本地演示模式下开通按时套餐'
  if (planType === BILLING_PLAN_KEYS.MONTHLY) return '已在本地演示模式下开通包月套餐'
  return '当前为免费试用模式'
}

export function getPlanAmount(planType) {
  if (planType === BILLING_PLAN_KEYS.HOURLY) return 99
  if (planType === BILLING_PLAN_KEYS.MONTHLY) return 1000
  return 0
}
