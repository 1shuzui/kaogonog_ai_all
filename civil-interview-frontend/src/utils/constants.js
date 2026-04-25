// 评分维度定义
export const DIMENSIONS = [
  { key: 'legal', name: '法治思维', maxScore: 20 },
  { key: 'practical', name: '实务落地', maxScore: 20 },
  { key: 'logic', name: '逻辑结构', maxScore: 15 },
  { key: 'expression', name: '语言表达', maxScore: 15 },
  { key: 'analysis', name: '综合分析', maxScore: 15 },
  { key: 'emergency', name: '应急应变', maxScore: 15 }
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
