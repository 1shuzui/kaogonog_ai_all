// 评分维度定义
export const DIMENSIONS = [
  { key: 'legal', name: '法治思维', maxScore: 20 },
  { key: 'practical', name: '实务落地', maxScore: 20 },
  { key: 'logic', name: '逻辑结构', maxScore: 15 },
  { key: 'expression', name: '语言表达', maxScore: 15 },
  { key: 'analysis', name: '综合分析', maxScore: 15 },
  { key: 'emergency', name: '应急应变', maxScore: 15 }
]

// 前端题型分类（用于专项训练和题型展示）
export const QUESTION_TYPE_NAME_MAP = {
  analysis: '综合分析',
  organization: '组织管理',
  practical: '组织管理',
  emergency: '应急应变',
  adaptability: '应急应变',
  interpersonal: '人际沟通',
  '人际沟通': '人际沟通',
  simulation: '现场模拟',
  expression: '现场模拟',
  career: '职业认知',
  '职业认知': '职业认知',
  legal: '职业认知',
  logic: '人际沟通'
}

export const TRAINING_CATEGORIES = [
  {
    key: 'analysis',
    name: '综合分析',
    requestDimension: 'analysis',
    progressKeys: ['analysis'],
    icon: '🔍',
    bgColor: '#E6FAFF',
    maxScore: 100
  },
  {
    key: 'organization',
    name: '组织管理',
    requestDimension: 'practical',
    progressKeys: ['organization', 'practical'],
    icon: '🗂️',
    bgColor: '#EAF7E6',
    maxScore: 100
  },
  {
    key: 'emergency',
    name: '应急应变',
    requestDimension: 'emergency',
    progressKeys: ['adaptability', 'emergency'],
    icon: '🚨',
    bgColor: '#FFF1F0',
    maxScore: 100
  },
  {
    key: 'interpersonal',
    name: '人际沟通',
    requestDimension: '人际沟通',
    progressKeys: ['interpersonal', 'logic'],
    icon: '🤝',
    bgColor: '#EEF4FF',
    maxScore: 100
  },
  {
    key: 'simulation',
    name: '现场模拟',
    requestDimension: 'expression',
    progressKeys: ['simulation', 'expression'],
    icon: '🎭',
    bgColor: '#FFF7E8',
    maxScore: 100
  },
  {
    key: 'career',
    name: '职业认知',
    requestDimension: '职业认知',
    progressKeys: ['career', 'legal'],
    icon: '🧭',
    bgColor: '#F5F0FF',
    maxScore: 100
  }
]

// 省份列表
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

// 考试状态
export const EXAM_STATUS = {
  IDLE: 'idle',
  PREPARING: 'preparing',
  ANSWERING: 'answering',
  SUBMITTING: 'submitting',
  COMPLETED: 'completed'
}

// 评级定义（公考面试四档配色）
export const GRADE_CONFIG = {
  A: { label: '优秀', color: '#389E0D', min: 85 },
  B: { label: '良好', color: '#1B5FAA', min: 75 },
  C: { label: '中等', color: '#D48806', min: 60 },
  D: { label: '待提升', color: '#CF1322', min: 0 }
}

export function getGrade(score, maxScore = 100) {
  const percent = (score / maxScore) * 100
  if (percent >= 85) return GRADE_CONFIG.A
  if (percent >= 75) return GRADE_CONFIG.B
  if (percent >= 60) return GRADE_CONFIG.C
  return GRADE_CONFIG.D
}

// 默认考试配置
export const DEFAULT_PREP_TIME = 90   // 秒
export const DEFAULT_ANSWER_TIME = 180 // 秒
export const MAX_ANSWER_TIME = 300     // 秒

// 维度提升建议
export const DIMENSION_TIPS = {
  '法治思维': '多练习法律法规类题目，熟悉《宪法》《行政法》等基本法律条文，注意在答题中引用具体法条依据。',
  '实务落地': '注重答题的可操作性，多使用"第一步...第二步..."的步骤化表达，结合实际工作场景提出具体措施。',
  '逻辑结构': '采用"总-分-总"或"是什么-为什么-怎么办"的框架，确保论点层次分明、前后呼应。',
  '语言表达': '注意语速适中、用词规范，避免口头禅，多使用政务规范用语，注意时间控制。',
  '综合分析': '全面看待问题，注意从正反两面分析，既要看到积极意义，也要指出潜在风险和改进方向。',
  '应急应变': '突发事件类题目要抓住"稳定局面-了解情况-分类处理-总结预防"的基本框架，体现冷静和担当。'
}

export const TRAINING_CATEGORY_TIPS = {
  '综合分析': '围绕社会现象、政策观点和公共议题，重点训练立场鲜明、分析全面、辩证作答的能力。',
  '组织管理': '重点练习活动策划、任务推进、统筹协调和复盘总结，作答时尽量体现步骤、节点和落地性。',
  '应急应变': '围绕突发事件、舆情处置和现场情况变化作答，优先体现稳控局面、快速研判、分类处置和复盘预防。',
  '人际沟通': '重点练习与领导、同事、群众和服务对象的沟通协调，答题时注意对象意识、情绪安抚、说服策略和关系修复。',
  '现场模拟': '尽量用口语化、场景化的方式直接开口作答，注意身份代入、交流对象、语气分寸和说服效果。',
  '职业认知': '围绕报考动机、岗位理解、价值取向和自我认知展开，重点体现政治素养、服务意识和岗位匹配度。'
}

// 薄弱维度阈值（低于此百分比标记为薄弱）
export const WEAK_THRESHOLD = 60

// 岗位系统
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

export function getQuestionTypeName(key) {
  return QUESTION_TYPE_NAME_MAP[key] || key
}

export function getTrainingCategory(key) {
  return TRAINING_CATEGORIES.find((item) => item.key === key) || null
}

export function mergeTrainingProgress(progressList = []) {
  const merged = {
    attempts: 0,
    totalScore: 0,
    bestScore: 0,
    recentScores: [],
    lastPracticeDate: null
  }

  for (const item of progressList) {
    if (!item) continue
    merged.attempts += Number(item.attempts || 0)
    merged.totalScore += Number(item.totalScore || 0)
    merged.bestScore = Math.max(merged.bestScore, Number(item.bestScore || 0))
    merged.recentScores.push(...(Array.isArray(item.recentScores) ? item.recentScores : []))

    const nextDate = item.lastPracticeDate ? new Date(item.lastPracticeDate).getTime() : 0
    const currentDate = merged.lastPracticeDate ? new Date(merged.lastPracticeDate).getTime() : 0
    if (nextDate > currentDate) {
      merged.lastPracticeDate = item.lastPracticeDate
    }
  }

  merged.recentScores = merged.recentScores.slice(-10)
  return merged
}
