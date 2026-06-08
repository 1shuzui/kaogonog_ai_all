/**
 * 这个工具文件处理 `scoringSupport` 这类跨页面规则；集中维护可以避免 PC、小程序或不同页面各自写一份判断。
 *
 * @param 无；文件级模块依赖导出函数、组合式 API 或调用方传入上下文。
 * @return 导出可复用的端侧能力，具体返回值由各公共函数保持兼容。
 * @raises 不主动吞掉业务异常；请求失败、权限不足和运行时错误交由调用方或全局拦截器处理。
 */
import { TRIAL_QUESTION } from '@/utils/billing'

const LOCAL_ONLY_QUESTION_ID_PATTERN = /^(?:train|training|gen|generated|local|temp|draft)_/i

export function isQuestionIdScoringSupported(questionId = '') {
  const normalizedId = String(questionId || '').trim()
  if (!normalizedId) return false
  if (normalizedId === TRIAL_QUESTION.id) return true

  return !LOCAL_ONLY_QUESTION_ID_PATTERN.test(normalizedId)
}

export function isQuestionScoringSupported(question = {}) {
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
