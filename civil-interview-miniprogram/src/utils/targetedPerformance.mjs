import { miniPracticeUrl, practiceFilterSummary } from '../../../shared/practiceSelection.mjs'

export const PERFORMANCE_TYPES = ['综合分析', '组织管理', '应急应变', '人际沟通', '情景模拟', '岗位认知']
export const periodOptions = [{ value: 'recent30', label: '近30天' }, { value: 'all', label: '全部记录' }]
export const practiceModes = [{ value: 'new', label: '练新题' }, { value: 'low_score', label: '重练低分题' }, { value: 'review', label: '复练已做题' }]
export const copy = value => JSON.parse(JSON.stringify(value))
export const reportKey = (target, period) => JSON.stringify([Object.entries(target || {}).sort(([a], [b]) => a.localeCompare(b)), period])

export function performanceScopeSummary(target = {}, provinces = []) {
  const track = { medical: '医疗系统考试', institution: '事业单位考试' }[target.examTrack]
  return [...new Set(practiceFilterSummary({ ...target, examCategory: track || target.examCategory }, provinces).split(' · '))].join(' · ')
}

export function readTargetedContext(raw) {
  if (!raw) return null
  let value = raw
  if (typeof value === 'string') {
    try { value = JSON.parse(value) }
    catch { try { value = JSON.parse(decodeURIComponent(value)) } catch { throw new Error('针对练习条件读取失败，请返回分析页重新选择') } }
  }
  if (!value || value.version !== 1 || !value.target || typeof value.target !== 'object' || Array.isArray(value.target)
    || !PERFORMANCE_TYPES.includes(value.questionType) || !['recent30', 'all'].includes(value.period)
    || !['new', 'low_score', 'review'].includes(value.mode) || ![1, 3, 5].includes(value.count)) {
    throw new Error('针对练习条件不完整，请返回分析页重新选择')
  }
  return copy(value)
}

export function practiceContext(target, questionType, period, overrides = {}) {
  return readTargetedContext({ version: 1, target, questionType, period, mode: 'new', count: 3, ...overrides })
}

export function targetedPracticeUrl(context, ids = []) {
  return miniPracticeUrl({ source: 'targeted', filters: context.target, questionIds: ids })
    + `&targetedContext=${encodeURIComponent(JSON.stringify(context))}`
}

export function performanceDetailUrl(target, period, questionType) {
  return `/pages/targeted/performance?target=${encodeURIComponent(JSON.stringify(target))}&period=${period}&questionType=${encodeURIComponent(questionType)}`
}

export function validateReport(data) {
  if (!data || !data.scopeKey || !data.analysisRevision || !data.target || !data.summary
    || !Array.isArray(data.questionTypes) || !data.rules || !(data.rules.minSamples > 0)
    || !(data.rules.lowThreshold < data.rules.highThreshold)) throw new Error('分析数据不完整，请重试')
  for (const row of data.questionTypes) {
    if (!PERFORMANCE_TYPES.includes(row.questionType) || !Number.isInteger(row.sampleCount) || row.sampleCount < 0
      || (row.sampleCount > 0 && (!Number.isFinite(row.averagePercent) || row.averagePercent < 0 || row.averagePercent > 100))
      || (row.sampleCount === 0 && row.averagePercent !== null)) throw new Error('分析分数或样本数无效，请重试')
  }
  return data
}
