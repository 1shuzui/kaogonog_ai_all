/** Display saved answers and placeholders without generating scores or review advice. */
import { getReviewTranscript } from './resultReview.mjs'
import { normalizeResult } from './scoring.js'
import { hasFinalScore } from './answerStatus.js'
import { getQuestionScorePair } from './scorePresentation.js'

export function isNoContentTranscript(value, scoring = {}) {
  const text = String(value || '').trim()
  const mode = String(scoring?.scoringMode || '').trim()
  return text ? !getReviewTranscript(value) : ['screened_zero', 'empty_zero'].includes(mode)
}

export function normalizeAnswerTiming(raw) {
  if (!raw || typeof raw !== 'object') return null
  const actualSeconds = Math.max(0, Number(raw.actualSeconds || raw.usageSeconds || 0) || 0)
  const standardSeconds = Math.max(0, Number(raw.standardSeconds || 0) || 0)
  const overtimeSeconds = Math.max(0, Number(raw.overtimeSeconds || (standardSeconds ? actualSeconds - standardSeconds : 0)) || 0)
  if (!actualSeconds && !standardSeconds) return null
  return { actualSeconds, standardSeconds, overtimeSeconds }
}

export function formatDuration(seconds = 0) {
  const total = Math.max(0, Math.round(Number(seconds) || 0))
  const minutes = Math.floor(total / 60)
  const rest = total % 60
  if (minutes <= 0) return `${rest} 秒`
  if (rest <= 0) return `${minutes} 分钟`
  return `${minutes} 分 ${rest} 秒`
}

export function resolveNoContentReason(value, scoring = {}) {
  if (!isNoContentTranscript(value, scoring)) return null
  const skipReason = String(scoring?.skipReason || scoring?.asrFailureType || scoring?.mediaRecord?.asrMeta?.status || '').trim()
  const reasonMap = {
    user_confirmed_skip: {
      title: '用户确认跳过',
      desc: '本题未提交录音或录像，已按未作答记 0 分。'
    },
    too_short: {
      title: '录音过短',
      desc: '本次录音时长不足，无法形成可靠文字稿，已按无效作答处理。'
    },
    silent_audio: {
      title: '音量过低或接近静音',
      desc: '本次录音没有足够清晰的人声，建议重新练习时靠近麦克风并保持环境安静。'
    },
    empty_audio: {
      title: '未识别到有效语音',
      desc: '本次录音未识别出可用于评分的作答内容。'
    },
    no_speech: {
      title: '未识别到有效语音',
      desc: '本次录音未识别出可用于评分的作答内容。'
    },
    funasr_error: {
      title: '语音服务异常',
      desc: '本次转写服务异常，建议重新录制后提交。'
    },
    asr_unavailable: {
      title: '语音服务异常',
      desc: '本次转写服务暂不可用，建议稍后重新录制后提交。'
    }
  }
  return reasonMap[skipReason] || {
    title: '无有效作答内容',
    desc: '本次没有可用于复盘的可靠文字稿，请完成一段清晰作答后再查看细化建议。'
  }
}

function getQuestionAssignedScore(question = {}) {
  const points = Array.isArray(question?.scoringPoints) ? question.scoringPoints : []
  return points.reduce((sum, item) => sum + (Number(item?.score || 0) || 0), 0)
}

export function normalizeDisplayResult(value = {}, question = {}) {
  const normalized = normalizeResult(value || {})
  const questionMaxScore = Number(normalized.questionMaxScore || getQuestionAssignedScore(question) || normalized.maxScore || 100) || 100
  return {
    ...normalized,
    // Keep supplied feedback only; score normalization must not manufacture review advice.
    answerImprovementSuggestion: value?.answerImprovementSuggestion || null,
    questionScore: Number(normalized.questionScore ?? normalized.totalScore ?? 0) || 0,
    questionMaxScore: questionMaxScore || 100
  }
}

export function buildEmptyResult(question = {}) {
  const maxScore = getQuestionAssignedScore(question) || 100
  return normalizeDisplayResult({
    totalScore: 0,
    maxScore,
    questionScore: 0,
    questionMaxScore: maxScore,
    grade: 'D',
    dimensions: [],
    aiComment: '本题未作答，按空答案记 0 分。',
    scoringMode: 'empty_zero'
  }, question)
}

export function buildDisplayAnswers(answers = [], questionIds = [], examId = '') {
  const answerMap = new Map()
  const normalizedAnswers = Array.isArray(answers) ? answers.filter(Boolean) : []
  normalizedAnswers.forEach((answer, index) => {
    const questionId = String(answer?.questionId || '').trim()
    if (!questionId) return
    answerMap.set(questionId, {
      ...answer,
      questionId,
      questionIndex: Number.isFinite(Number(answer?.questionIndex)) ? Number(answer.questionIndex) : index
    })
  })

  const order = Array.isArray(questionIds) ? questionIds.map((id) => String(id || '').trim()).filter(Boolean) : []
  if (order.length) {
    const ordered = order.map((questionId, index) => {
      const matched = answerMap.get(questionId)
      if (matched) return { ...matched, questionIndex: index }
      return {
        examId,
        questionId,
        questionIndex: index,
        questionStem: '',
        province: 'national',
        transcript: '',
        scoringResult: null,
        answerTiming: null,
        isPlaceholder: true
      }
    })
    const appended = normalizedAnswers.filter((answer) => !order.includes(String(answer?.questionId || '').trim()))
    return [...ordered, ...appended]
  }

  return normalizedAnswers.sort((a, b) => {
    const aIndex = Number.isFinite(Number(a?.questionIndex)) ? Number(a.questionIndex) : 0
    const bIndex = Number.isFinite(Number(b?.questionIndex)) ? Number(b.questionIndex) : 0
    return aIndex - bIndex
  })
}

export function formatAnswerScore(answer = {}) {
  if (answer.isPlaceholder) return '未作答'
  if (!hasFinalScore(answer.scoringResult)) return '待点评'
  const scoring = normalizeDisplayResult(answer.scoringResult)
  const { score, maxScore } = getQuestionScorePair(scoring)
  return `${score}/${maxScore}分`
}
