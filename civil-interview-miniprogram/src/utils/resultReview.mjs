// View-only extraction. Never infer feedback from a score or fill missing advice.
const text = value => typeof value === 'string' ? value.trim() : ''
const list = value => Array.isArray(value) ? value : []

export function readReviewSuggestion(value) {
  if (!value || typeof value !== 'object' || Array.isArray(value)) return null
  const result = {
    source: text(value.source),
    summary: text(value.summary),
    teacherComment: text(value.teacherComment ?? value.teacher_comment),
    diagnosisItems: list(value.diagnosisItems ?? value.diagnosis_items).map(text).filter(Boolean),
    focusPoints: list(value.focusPoints ?? value.focus_points).map((item, index) => ({
      order: String(item?.order || index + 1),
      title: text(typeof item === 'string' ? item : item?.title ?? item?.name),
      hint: text(item?.hint ?? item?.content ?? item?.description)
    })).filter(item => item.title || item.hint),
    missingKeywords: list(value.missingKeywords ?? value.missing_keywords).map(text).filter(Boolean),
    expressionUpgrades: list(value.expressionUpgrades ?? value.expression_upgrades).map(item => ({
      before: text(item?.before ?? item?.weak),
      after: text(typeof item === 'string' ? item : item?.after ?? item?.upgrade ?? item?.suggestion)
    })).filter(item => item.before || item.after),
    sampleAnswer: text(value.sampleAnswer ?? value.sample_answer),
    rewriteOpening: text(value.rewriteOpening ?? value.rewrite_opening),
    rewriteClosing: text(value.rewriteClosing ?? value.rewrite_closing)
  }
  return Object.entries(result).some(([key, value]) => key !== 'source' && value.length) ? result : null
}

export function getReviewPriorities(suggestion) {
  // A generic fallback is not evidence of an individual weakness.
  if (suggestion?.source !== 'model') return []
  const candidates = [
    ...suggestion.focusPoints.map(item => ({ title: item.title, text: item.hint })),
    ...suggestion.expressionUpgrades.filter(item => item.after).map(item => ({ title: '表达调整', text: item.after })),
    { title: '开头调整', text: suggestion.rewriteOpening },
    { title: '结尾调整', text: suggestion.rewriteClosing }
  ]
  const seen = new Set()
  return candidates.filter(item => {
    if (!item.title && !item.text) return false
    if (!item.text && ['开头调整', '结尾调整'].includes(item.title)) return false
    const key = `${item.title}\n${item.text}`
    if (seen.has(key)) return false
    seen.add(key)
    return true
  }).slice(0, 3)
}

export function getReviewTranscript(value) {
  if (typeof value !== 'string') return ''
  const trimmed = value.trim()
  const placeholders = ['未作答', '未能识别出有效语音', '未配置真实语音转写服务', '当前未配置真实语音转写服务', '无法生成可靠文字稿']
  return !trimmed || placeholders.includes(trimmed) ? '' : value
}
