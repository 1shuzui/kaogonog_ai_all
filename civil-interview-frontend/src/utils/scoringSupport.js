const USE_MOCK = import.meta.env.VITE_USE_MOCK === 'true'
const LOCAL_ONLY_QUESTION_ID_PATTERN = /^q(?:_|[0-9])/i

export function isQuestionIdScoringSupported(questionId = '') {
  if (USE_MOCK) return true

  const normalizedId = String(questionId || '').trim()
  if (!normalizedId) return false

  return !LOCAL_ONLY_QUESTION_ID_PATTERN.test(normalizedId)
}

export function isQuestionScoringSupported(question = {}) {
  if (USE_MOCK) return true
  return isQuestionIdScoringSupported(question?.id)
}

export function splitScoringSupportedQuestions(questions = []) {
  const supported = []
  const unsupported = []

  for (const question of Array.isArray(questions) ? questions : []) {
    if (isQuestionScoringSupported(question)) {
      supported.push(question)
    } else {
      unsupported.push(question)
    }
  }

  return { supported, unsupported }
}

export function getScoringUnavailableText(count = 1) {
  return count > 1
    ? `已跳过 ${count} 道未接入评分题库的题目`
    : '当前题目未接入评分题库'
}

export function getScoringUnavailableMessage(count = 1) {
  return `${getScoringUnavailableText(count)}，暂时无法使用外部评分。`
}

export function normalizeScoringErrorMessage(rawMessage = '') {
  const message = String(rawMessage || '').trim()

  if (!message) return ''

  if (message.includes('评分引擎中未找到该题目')) {
    return '当前题目未同步到评分题库，暂时无法评分，请更换题目或联系管理员同步。'
  }

  if (message.includes('Question not found')) {
    return '当前题目不存在或已被移除，请返回重新选择题目。'
  }

  return message
}
