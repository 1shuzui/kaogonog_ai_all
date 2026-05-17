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
      name: item?.name === '法治思维' ? '行政思维' : item?.name || item?.key || '能力维度',
      key: item?.key || item?.name || '',
      score,
      maxScore,
      percent: Math.max(0, Math.min(100, Math.round((score / maxScore) * 100)))
    }
  })
}

function normalizeTextList(value, limit = 6) {
  if (!Array.isArray(value)) return []
  return value
    .map((item) => String(item || '').trim())
    .filter(Boolean)
    .slice(0, limit)
}

function normalizeFocusPoints(value) {
  if (!Array.isArray(value)) return []
  return value
    .map((item, index) => {
      if (item && typeof item === 'object') {
        return {
          order: String(item.order || index + 1),
          title: String(item.title || item.name || '').trim(),
          hint: String(item.hint || item.content || item.description || '').trim()
        }
      }
      return {
        order: String(index + 1),
        title: String(item || '').trim(),
        hint: ''
      }
    })
    .filter((item) => item.title || item.hint)
    .slice(0, 4)
}

function normalizeExpressionUpgrades(value) {
  if (!Array.isArray(value)) return []
  return value
    .map((item) => {
      if (item && typeof item === 'object') {
        return {
          before: String(item.before || item.weak || '').trim(),
          after: String(item.after || item.upgrade || item.suggestion || '').trim()
        }
      }
      return {
        before: '',
        after: String(item || '').trim()
      }
    })
    .filter((item) => item.before || item.after)
    .slice(0, 4)
}

function buildFallbackImprovementSuggestion(totalScore = 0, maxScore = 100) {
  const ratio = maxScore ? totalScore / maxScore : 0
  const summary = ratio >= 0.75
    ? '本次作答基础较好，下一步重点提升岗位化细节和表达精度。'
    : '建议先补齐审题、分层和具体措施，再提升表达完整度。'
  return {
    source: 'fallback',
    summary,
    teacherComment: '先把题干任务说清楚，再用可执行的步骤回应问题，结尾形成复盘闭环。',
    diagnosisItems: ['要点展开还可以更具体', '岗位动作和群众视角需要进一步压实'],
    focusPoints: [
      { order: '1', title: '先扣题', hint: '开头直接回应题干中的对象、矛盾和处理目标。' },
      { order: '2', title: '补措施', hint: '围绕核实、沟通、协调、落实、反馈分层展开。' },
      { order: '3', title: '收闭环', hint: '结尾说明复盘改进和后续跟踪。' }
    ],
    missingKeywords: ['群众立场', '依法依规', '闭环反馈'],
    expressionUpgrades: [
      { before: '我会处理好。', after: '我会先核实情况，再协调资源按职责推进解决。' },
      { before: '加强沟通。', after: '主动解释政策依据和办理流程，并及时反馈阶段进展。' }
    ],
    sampleAnswer: '可以按照“表明态度、分析原因、提出措施、总结提升”的结构展开，重点体现群众立场、依法履职和闭环落实。',
    rewriteOpening: '各位考官，我认为这道题的关键是既回应现实问题，也把工作责任落到可执行步骤上。',
    rewriteClosing: '后续我会做好复盘总结，把一次问题处置转化为改进流程、提升服务的机会。'
  }
}

export function normalizeImprovementSuggestion(value, totalScore = 0, maxScore = 100) {
  const fallback = buildFallbackImprovementSuggestion(totalScore, maxScore)
  if (!value || typeof value !== 'object') return fallback
  const diagnosisItems = normalizeTextList(value.diagnosisItems || value.diagnosis_items)
  const focusPoints = normalizeFocusPoints(value.focusPoints || value.focus_points)
  const missingKeywords = normalizeTextList(value.missingKeywords || value.missing_keywords, 8)
  const expressionUpgrades = normalizeExpressionUpgrades(value.expressionUpgrades || value.expression_upgrades)
  return {
    source: value.source === 'model' ? 'model' : 'fallback',
    summary: String(value.summary || fallback.summary).trim(),
    teacherComment: String(value.teacherComment || value.teacher_comment || fallback.teacherComment).trim(),
    diagnosisItems: diagnosisItems.length ? diagnosisItems : fallback.diagnosisItems,
    focusPoints: focusPoints.length ? focusPoints : fallback.focusPoints,
    missingKeywords: missingKeywords.length ? missingKeywords : fallback.missingKeywords,
    expressionUpgrades: expressionUpgrades.length ? expressionUpgrades : fallback.expressionUpgrades,
    sampleAnswer: String(value.sampleAnswer || value.sample_answer || fallback.sampleAnswer).trim(),
    rewriteOpening: String(value.rewriteOpening || value.rewrite_opening || fallback.rewriteOpening).trim(),
    rewriteClosing: String(value.rewriteClosing || value.rewrite_closing || fallback.rewriteClosing).trim()
  }
}

export function normalizeResult(result = {}) {
  const totalScore = Number(result?.totalScore ?? result?.score ?? 0) || 0
  const maxScore = Number(result?.maxScore ?? 100) || 100
  return {
    ...result,
    totalScore,
    maxScore,
    dimensions: normalizeDimensions(result?.dimensions),
    aiComment: result?.aiComment || result?.comment || '暂无评语',
    answerImprovementSuggestion: normalizeImprovementSuggestion(
      result?.answerImprovementSuggestion,
      totalScore,
      maxScore
    )
  }
}

export function scoringUnavailableMessage(count = 1) {
  return count > 1
    ? `已跳过 ${count} 道未接入评分题库的题目`
    : '当前题目未接入评分题库，暂时无法评分'
}
