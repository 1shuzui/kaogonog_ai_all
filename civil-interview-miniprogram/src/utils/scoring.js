import { DIMENSION_FALLBACKS } from './constants'

const LOCAL_ONLY_QUESTION_ID_PATTERN = /^q(?:_|[0-9])/i

export function isQuestionIdScoringSupported(questionId = '') {
  const normalized = String(questionId || '').trim()
  if (!normalized) return false
  return !LOCAL_ONLY_QUESTION_ID_PATTERN.test(normalized)
}

export function isQuestionScoringSupported(question = {}) {
  return isQuestionIdScoringSupported(question?.id)
}

export function normalizeDimensions(dimensions = []) {
  const source = Array.isArray(dimensions) && dimensions.length ? dimensions : DIMENSION_FALLBACKS
  return source.map((item) => {
    const score = Number(item?.score ?? item?.avg ?? 0) || 0
    const maxScore = Number(item?.maxScore ?? 100) || 100
    return {
      name: item?.name || item?.key || '能力维度',
      key: item?.key || item?.name || '',
      score,
      maxScore,
      percent: Math.max(0, Math.min(100, Math.round((score / maxScore) * 100)))
    }
  })
}

export function normalizeResult(result = {}) {
  const totalScore = Number(result?.totalScore ?? result?.score ?? 0) || 0
  const maxScore = Number(result?.maxScore ?? 100) || 100
  return {
    ...result,
    totalScore,
    maxScore,
    dimensions: normalizeDimensions(result?.dimensions),
    aiComment: result?.aiComment || result?.comment || '暂无评语'
  }
}

export function scoringUnavailableMessage(count = 1) {
  return count > 1
    ? `已跳过 ${count} 道未接入评分题库的题目`
    : '当前题目未接入评分题库，暂时无法评分'
}
