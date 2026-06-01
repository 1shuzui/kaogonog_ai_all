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
  '完整全真模拟与录音/录像评分',
  '定向备考与岗位/省份题源',
  '专项训练与薄弱维度推荐',
  '历史报告、错题本与收藏夹'
]

export const TRIAL_QUESTION = {
  id: 'q001',
  dimension: '综合分析',
  questionType: '结构化面试',
  sourceLabel: '试用题'
}

const BILLING_COPY_MAP = {
  'Full exam': '完整全真模拟',
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
  'Hourly access activated in local demo mode': '按时套餐已开通',
  'Monthly access activated in local demo mode': '包月套餐已开通'
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
      '可完成录音或录像提交并查看一次评分流程',
      '可查看结果页、维度条和基础复盘结构',
      '适合首次检查麦克风、摄像头和评分流程'
    ]
  },
  {
    key: BILLING_PLAN_KEYS.HOURLY,
    packageCode: 'trial_3h',
    badge: '按时',
    title: '3小时体验包',
    priceText: '¥99',
    description: '适合临近面试前的集中冲刺和短时高强度练习。',
    features: [
      '解锁全真模拟、定向备考、专项训练和题库推荐',
      '总计 3 小时训练时长，按实际使用消耗',
      '可与已开通套餐叠加，系统优先消耗更早到期的权益',
      '支持查看历史报告、收藏题和低分错题',
      '适合临近面试前集中冲刺'
    ]
  },
  {
    key: BILLING_PLAN_KEYS.MONTHLY,
    packageCode: 'monthly_1h_day',
    badge: '包月',
    title: '包月每日1小时',
    priceText: '¥299',
    description: '适合系统化备考和连续多天的稳定训练。',
    features: [
      '30 天有效期，每日 1 小时训练额度',
      '解锁全真模拟、定向备考、专项训练和题库推荐',
      '可与按时套餐或续费权益叠加，剩余额度统一汇总',
      '支持历史报告、收藏/错题复盘和智能推荐',
      '适合按日推进、持续复盘的备考节奏'
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
  if (planType === BILLING_PLAN_KEYS.MONTHLY) return '包月每日1小时'
  return '免费试用'
}

export function getPlanActivationSummary(planType) {
  if (planType === BILLING_PLAN_KEYS.HOURLY) return '按时套餐已开通'
  if (planType === BILLING_PLAN_KEYS.MONTHLY) return '包月套餐已开通'
  return '当前为免费试用模式'
}

export function getPlanAmount(planType) {
  if (planType === BILLING_PLAN_KEYS.HOURLY) return 99
  if (planType === BILLING_PLAN_KEYS.MONTHLY) return 299
  return 0
}
