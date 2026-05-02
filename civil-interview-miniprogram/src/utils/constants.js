export const TOKEN_STORAGE_KEY = 'token'
export const USERNAME_STORAGE_KEY = 'username'
export const PROVINCE_STORAGE_KEY = 'civil_selected_province'
export const PREFERENCES_STORAGE_KEY = 'civil_user_preferences'
export const TRAINING_PROGRESS_STORAGE_KEY = 'civil_training_progress'
export const BILLING_STORAGE_KEY = 'civil_mini_billing_state'

export const DEFAULT_PREFERENCES = {
  defaultPrepTime: 90,
  defaultAnswerTime: 180,
  enableAudio: true
}

export const PROVINCES = [
  { code: 'national', name: '国考' },
  { code: 'beijing', name: '北京' },
  { code: 'shanghai', name: '上海' },
  { code: 'guangdong', name: '广东' },
  { code: 'jiangsu', name: '江苏' },
  { code: 'zhejiang', name: '浙江' },
  { code: 'shandong', name: '山东' },
  { code: 'sichuan', name: '四川' },
  { code: 'hubei', name: '湖北' },
  { code: 'hunan', name: '湖南' },
  { code: 'henan', name: '河南' },
  { code: 'hebei', name: '河北' },
  { code: 'fujian', name: '福建' },
  { code: 'anhui', name: '安徽' },
  { code: 'liaoning', name: '辽宁' },
  { code: 'shaanxi', name: '陕西' }
]

export const QUESTION_CATEGORIES = [
  { key: '', name: '全部题型' },
  { key: 'analysis', name: '综合分析' },
  { key: 'practical', name: '组织管理' },
  { key: 'emergency', name: '应急应变' },
  { key: 'logic', name: '人际沟通' },
  { key: 'expression', name: '现场模拟' },
  { key: 'legal', name: '职业认知' }
]

export const TRAINING_CATEGORIES = [
  {
    key: 'analysis',
    name: '综合分析',
    requestDimension: 'analysis',
    icon: '析',
    tone: '#e6f4ff',
    maxScore: 100,
    tip: '训练政策观点、社会现象和公共议题的辩证分析。'
  },
  {
    key: 'organization',
    name: '组织管理',
    requestDimension: 'practical',
    icon: '组',
    tone: '#eaf7e6',
    maxScore: 100,
    tip: '训练活动策划、统筹推进、复盘总结和落地执行。'
  },
  {
    key: 'emergency',
    name: '应急应变',
    requestDimension: 'emergency',
    icon: '急',
    tone: '#fff1f0',
    maxScore: 100,
    tip: '训练稳控现场、快速研判、分类处置和复盘预防。'
  },
  {
    key: 'interpersonal',
    name: '人际沟通',
    requestDimension: '人际沟通',
    icon: '沟',
    tone: '#eef4ff',
    maxScore: 100,
    tip: '训练对象意识、情绪安抚、说服策略和关系修复。'
  },
  {
    key: 'simulation',
    name: '现场模拟',
    requestDimension: 'expression',
    icon: '演',
    tone: '#fff7e8',
    maxScore: 100,
    tip: '训练身份代入、语气分寸和场景化表达。'
  },
  {
    key: 'career',
    name: '职业认知',
    requestDimension: '职业认知',
    icon: '岗',
    tone: '#f5f0ff',
    maxScore: 100,
    tip: '训练报考动机、岗位理解、价值取向和服务意识。'
  }
]

export const POSITION_SYSTEMS = [
  { code: 'tax', name: '税务系统' },
  { code: 'customs', name: '海关系统' },
  { code: 'police', name: '公安系统' },
  { code: 'court', name: '法院系统' },
  { code: 'procurate', name: '检察系统' },
  { code: 'market', name: '市场监管' },
  { code: 'general', name: '综合管理' },
  { code: 'township', name: '乡镇基层' },
  { code: 'finance', name: '银保监会' },
  { code: 'diplomacy', name: '外交系统' }
]

export const GRADE_CONFIG = {
  A: { label: '优秀', color: '#389e0d', min: 85 },
  B: { label: '良好', color: '#1b5faa', min: 75 },
  C: { label: '中等', color: '#d48806', min: 60 },
  D: { label: '待提升', color: '#cf1322', min: 0 }
}

export const DIMENSION_FALLBACKS = [
  { name: '综合分析', key: 'analysis', score: 0, maxScore: 20 },
  { name: '实务落地', key: 'practical', score: 0, maxScore: 20 },
  { name: '应急应变', key: 'emergency', score: 0, maxScore: 15 },
  { name: '法治思维', key: 'legal', score: 0, maxScore: 15 },
  { name: '逻辑结构', key: 'logic', score: 0, maxScore: 15 },
  { name: '语言表达', key: 'expression', score: 0, maxScore: 15 }
]

export function getProvinceName(code) {
  return PROVINCES.find((item) => item.code === code)?.name || '国考'
}

export function getCategoryName(key) {
  return QUESTION_CATEGORIES.find((item) => item.key === key)?.name || key || '综合题'
}

export function getTrainingCategory(key) {
  return TRAINING_CATEGORIES.find((item) => item.key === key) || TRAINING_CATEGORIES[0]
}

export function getGrade(score, maxScore = 100) {
  const percent = maxScore > 0 ? (Number(score || 0) / maxScore) * 100 : 0
  if (percent >= 85) return GRADE_CONFIG.A
  if (percent >= 75) return GRADE_CONFIG.B
  if (percent >= 60) return GRADE_CONFIG.C
  return GRADE_CONFIG.D
}
