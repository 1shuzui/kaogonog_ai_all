/**
 * 小程序考试状态仓库，保存当前考试、题目队列、全真模拟上下文、媒体提交状态和评分结果跳转信息。
 *
 * 录音、上传、评分和结果页之间需要共享状态，放在 store 可以避免页面返回或切换时丢失关键上下文。
 * 这里不保存作答前可见的题目分数，分数只在评分完成后进入结果状态。
 *
 * @param 无；actions 接收抽题参数、考试 ID、媒体文件和提交内容。
 * @return 导出 Pinia store，供准备页、考场页和结果页共享考试流程。
 * @raises Error: 创建考试、上传答案、完成考试或评分失败时由 action 抛给页面处理。
 */
import { defineStore } from 'pinia'
import { startExam, uploadRecording, completeExam } from '../api/exam'
import { evaluateAnswer, transcribeAudio } from '../api/scoring'
import { prepareMediaForUpload } from '../utils/mediaUpload'
import { normalizeResult } from '../utils/scoring'

const EMPTY_TRANSCRIPT_TEXT = '未作答'
const PLACEHOLDER_TRANSCRIPT_MARKERS = [
  '未能识别出有效语音',
  '未配置真实语音转写服务',
  '无法生成可靠文字稿',
  '当前未配置真实语音转写服务'
]
const USER_INVALID_ASR_STATUSES = new Set(['too_short', 'silent_audio', 'empty_audio', 'no_speech'])
const SERVICE_FAILURE_ASR_STATUSES = new Set(['funasr_error', 'asr_unavailable', 'service_unavailable', 'unavailable', 'timeout', 'error'])
const answerProcessingTasks = new Map()

function buildZeroScoreResult(options = {}) {
  const skipReason = String(options.skipReason || '').trim()
  const asrFailureType = String(options.asrFailureType || '').trim()
  const answerTiming = options.answerTiming && typeof options.answerTiming === 'object' ? options.answerTiming : null
  return normalizeResult({
    totalScore: 0,
    maxScore: 100,
    grade: 'D',
    dimensions: [
      { name: '综合分析', key: 'analysis', score: 0, maxScore: 20 },
      { name: '实务落地', key: 'practical', score: 0, maxScore: 20 },
      { name: '应急应变', key: 'emergency', score: 0, maxScore: 15 },
      { name: '行政思维', key: 'legal', score: 0, maxScore: 15 },
      { name: '逻辑结构', key: 'logic', score: 0, maxScore: 15 },
      { name: '语言表达', key: 'expression', score: 0, maxScore: 15 }
    ],
    aiComment: options.aiComment || '本题未提交有效作答内容，按空答案记 0 分。',
    scoringMode: 'empty_zero',
    ...(skipReason ? { skipReason } : {}),
    ...(asrFailureType ? { asrFailureType } : {}),
    ...(answerTiming ? { answerTiming } : {})
  })
}

function mergeAnswerMetaIntoResult(result, answerMeta = {}) {
  if (!answerMeta || typeof answerMeta !== 'object') return normalizeResult(result)
  return normalizeResult({
    ...result,
    ...(answerMeta.answerTiming ? { answerTiming: answerMeta.answerTiming } : {}),
    ...(answerMeta.skipReason ? { skipReason: answerMeta.skipReason } : {}),
    ...(answerMeta.asrFailureType ? { asrFailureType: answerMeta.asrFailureType } : {}),
    ...(answerMeta.asrStatus ? { asrStatus: answerMeta.asrStatus } : {}),
    ...(answerMeta.asrMessage ? { asrMessage: answerMeta.asrMessage } : {})
  })
}

function normalizeAsrStatus(result = {}) {
  return String(result?.asrMeta?.status || result?.status || '').trim().toLowerCase()
}

function isPlaceholderTranscript(text = '') {
  const normalized = String(text || '').trim()
  return !normalized || PLACEHOLDER_TRANSCRIPT_MARKERS.some((marker) => normalized.includes(marker))
}

function shouldRetryTranscribeResult(result = {}) {
  const transcript = String(result?.transcript || '').trim()
  return Boolean(result?.needsRetry) || isPlaceholderTranscript(transcript)
}

function isServiceAsrFailure(result = {}, error = null) {
  const status = normalizeAsrStatus(result)
  if (SERVICE_FAILURE_ASR_STATUSES.has(status)) return true
  if (error) return true
  const transcript = String(result?.transcript || '').trim()
  return PLACEHOLDER_TRANSCRIPT_MARKERS.some((marker) => transcript.includes(marker))
}

function isUserInvalidAsr(result = {}) {
  return USER_INVALID_ASR_STATUSES.has(normalizeAsrStatus(result))
}

function buildAsrError(message, result = {}, fallbackType = 'asr_unavailable') {
  const error = new Error(message || '语音识别失败，请重新录制')
  const status = normalizeAsrStatus(result)
  error.asrFailureType = status || fallbackType
  error.asrMeta = result?.asrMeta || {}
  error.asrMessage = result?.message || message || ''
  error.userInvalid = USER_INVALID_ASR_STATUSES.has(error.asrFailureType)
  error.serviceFailure = SERVICE_FAILURE_ASR_STATUSES.has(error.asrFailureType) || fallbackType === 'asr_unavailable'
  return error
}

async function transcribeAudioWithRetry(filePath, options = {}) {
  let lastResult = null
  let lastError = null
  for (let attempt = 0; attempt < 2; attempt += 1) {
    try {
      const result = await transcribeAudio(filePath, options)
      lastResult = { ...result, retryCount: attempt }
      if (!shouldRetryTranscribeResult(result)) return lastResult
    } catch (error) {
      lastError = error
    }
  }
  if (lastError) {
    throw buildAsrError(lastError?.message || '语音服务异常，请稍后重试', {}, 'asr_unavailable')
  }
  return lastResult || {}
}

async function evaluateEmptyAnswer(questionId, examId, options = {}) {
  const answerMeta = options.answerMeta || {}
  if (!examId) return buildZeroScoreResult({ ...options, ...answerMeta })
  try {
    return mergeAnswerMetaIntoResult(await evaluateAnswer({
      questionId,
      transcript: '',
      examId,
      answerMeta
    }), answerMeta)
  } catch {
    return buildZeroScoreResult({ ...options, ...answerMeta })
  }
}

export const useExamStore = defineStore('exam', {
  state: () => ({
    examId: '',
    questions: [],
    currentIndex: 0,
    answers: [],
    latestResult: null,
    latestTranscript: '',
    loading: false,
    source: '',
    mediaMode: 'audio'
  }),

  getters: {
    currentQuestion(state) {
      return state.questions[state.currentIndex] || null
    },
    questionNumber(state) {
      return state.currentIndex + 1
    },
    totalQuestions(state) {
      return state.questions.length
    },
    isLastQuestion(state) {
      return state.currentIndex >= state.questions.length - 1
    }
  },

  actions: {
    async startFromQuestions(questions = [], source = '') {
      const list = Array.isArray(questions) ? questions.filter(Boolean) : []
      if (!list.length) throw new Error('暂无可用题目')
      const response = await startExam(list.map((item) => item.id))
      this.examId = response.examId
      this.questions = list
      this.currentIndex = 0
      this.answers = []
      this.latestResult = null
      this.latestTranscript = ''
      this.source = source
      answerProcessingTasks.clear()
      return response
    },

    async submitCurrentAnswer({
      filePath = '',
      mediaType = 'audio',
      audioFilePath = '',
      skipConfirmed = false,
      skipReason = '',
      timingMeta = null,
      waitForProcessing = true
    } = {}) {
      const question = this.currentQuestion
      if (!question) throw new Error('当前题目不存在')
      if (!this.examId) throw new Error('考试会话不存在，请重新开始')

      this.loading = true
      try {
        const hasAnswerPayload = !!filePath

        if (!hasAnswerPayload) {
          if (!skipConfirmed) throw new Error('当前没有录音或录像，请先录制后提交')
          const answerMeta = {
            skipReason: skipReason || 'user_confirmed_skip',
            ...(timingMeta ? { answerTiming: timingMeta } : {})
          }
          const result = await evaluateEmptyAnswer(question.id, this.examId, {
            answerMeta,
            skipReason: answerMeta.skipReason,
            answerTiming: timingMeta,
            aiComment: answerMeta.skipReason === 'user_confirmed_skip'
              ? '用户确认跳过本题，按未作答记 0 分。'
              : '本题未形成有效语音内容，按无效作答记 0 分。'
          })
          const answer = {
            examId: this.examId,
            questionId: question.id,
            questionStem: question.stem,
            questionIndex: this.currentIndex,
            province: question.province,
            transcript: EMPTY_TRANSCRIPT_TEXT,
            scoringResult: result,
            answerTiming: timingMeta,
            skipReason: answerMeta.skipReason,
            submittedAt: new Date().toISOString(),
            processingStatus: 'completed'
          }
          this.answers = [
            ...this.answers.filter((item) => item.questionIndex !== this.currentIndex),
            answer
          ].sort((a, b) => a.questionIndex - b.questionIndex)
          this.latestResult = result
          this.latestTranscript = EMPTY_TRANSCRIPT_TEXT
          return answer
        }

        const answer = {
          examId: this.examId,
          questionId: question.id,
          questionStem: question.stem,
          questionIndex: this.currentIndex,
          province: question.province,
          filePath,
          mediaType,
          audioFilePath,
          answerTiming: timingMeta,
          transcript: '',
          scoringResult: null,
          submittedAt: new Date().toISOString(),
          processingStatus: 'queued',
          processingError: ''
        }
        this.answers = [
          ...this.answers.filter((item) => item.questionIndex !== this.currentIndex),
          answer
        ].sort((a, b) => a.questionIndex - b.questionIndex)
        this.latestResult = null
        this.latestTranscript = ''
        const task = this.queueAnswerProcessing(answer)
        if (waitForProcessing !== false) {
          const processed = await task
          if (processed.processingStatus === 'failed') {
            const error = new Error(processed.processingError || '评分失败')
            error.asrFailureType = processed.asrFailureType || ''
            error.asrMessage = processed.asrMessage || processed.processingError || ''
            error.userInvalid = processed.userInvalid === true
            error.serviceFailure = processed.serviceFailure === true
            throw error
          }
          return processed
        }
        return answer
      } finally {
        this.loading = false
      }
    },

    queueAnswerProcessing(answer) {
      const taskKey = `${answer.examId}:${answer.questionIndex}`
      const task = this.processAnswer(answer)
        .catch((error) => {
          answer.processingStatus = 'failed'
          answer.processingError = error?.message || '评分失败'
          answer.asrFailureType = error?.asrFailureType || ''
          answer.asrMessage = error?.asrMessage || ''
          answer.userInvalid = error?.userInvalid === true
          answer.serviceFailure = error?.serviceFailure === true
          return answer
        })
        .finally(() => {
          answerProcessingTasks.delete(taskKey)
        })
      answerProcessingTasks.set(taskKey, task)
      return task
    },

    async processAnswer(answer) {
      let transcript = ''
      const mediaType = answer.mediaType || 'audio'
      answer.processingStatus = answer.filePath ? 'uploading' : 'scoring'

      if (answer.filePath) {
        const uploadMedia = await prepareMediaForUpload(answer.filePath, mediaType)
        const transcriptionMedia = mediaType === 'video' && answer.audioFilePath
          ? await prepareMediaForUpload(answer.audioFilePath, 'audio')
          : uploadMedia

        await uploadRecording(answer.examId, answer.questionId, uploadMedia.filePath, {
          mediaType,
          source: uploadMedia.compressed
            ? `miniapp_${mediaType}_recording_compressed`
            : `miniapp_${mediaType}_recording`
        })
        if (!transcript) {
          answer.processingStatus = 'transcribing'
          const transcribeResult = await transcribeAudioWithRetry(transcriptionMedia.filePath, {
            mediaType: transcriptionMedia.mediaType || mediaType,
            questionId: answer.questionId
          })
          if (isServiceAsrFailure(transcribeResult)) {
            throw buildAsrError(
              transcribeResult?.message || '语音服务异常，请重新录制后再提交',
              transcribeResult,
              'asr_unavailable'
            )
          }
          if (isUserInvalidAsr(transcribeResult) || isPlaceholderTranscript(transcribeResult?.transcript)) {
            const status = normalizeAsrStatus(transcribeResult) || 'no_speech'
            const messageMap = {
              too_short: '录音时间过短，请重新录制',
              silent_audio: '录音音量过低或接近静音，请重新录制',
              empty_audio: '未识别到有效语音，请重新录制',
              no_speech: '未识别到有效语音，请重新录制'
            }
            throw buildAsrError(
              transcribeResult?.message || messageMap[status] || '未识别到有效语音，请重新录制',
              { ...transcribeResult, asrMeta: { ...(transcribeResult?.asrMeta || {}), status } },
              status
            )
          }
          transcript = String(transcribeResult?.transcript || '').trim()
          answer.asrMeta = transcribeResult?.asrMeta || {}
        }
      }

      answer.processingStatus = 'scoring'
      const answerMeta = {
        ...(answer.answerTiming ? { answerTiming: answer.answerTiming } : {}),
        ...(answer.asrMeta?.status ? { asrStatus: answer.asrMeta.status } : {}),
        ...(answer.asrMeta?.message ? { asrMessage: answer.asrMeta.message } : {})
      }
      const result = transcript
        ? mergeAnswerMetaIntoResult(await evaluateAnswer({
          questionId: answer.questionId,
          transcript,
          examId: answer.examId,
          answerMeta
        }), answerMeta)
        : await evaluateEmptyAnswer(answer.questionId, answer.examId, { answerMeta })

      answer.transcript = transcript || EMPTY_TRANSCRIPT_TEXT
      answer.scoringResult = result
      answer.processingStatus = 'completed'

      if (this.examId === answer.examId && this.currentIndex === answer.questionIndex) {
        this.latestResult = result
        this.latestTranscript = answer.transcript
      }

      return answer
    },

    async waitForPendingProcessing() {
      if (!answerProcessingTasks.size) return
      await Promise.allSettled(Array.from(answerProcessingTasks.values()))
    },

    goNext() {
      if (!this.isLastQuestion) {
        this.currentIndex += 1
        this.latestResult = null
        this.latestTranscript = ''
        return true
      }
      return false
    },

    async finish() {
      await this.waitForPendingProcessing()
      if (this.examId) {
        await completeExam(this.examId).catch(() => null)
      }
    },

    reset() {
      this.examId = ''
      this.questions = []
      this.currentIndex = 0
      this.answers = []
      this.latestResult = null
      this.latestTranscript = ''
      this.loading = false
      this.source = ''
      this.mediaMode = 'audio'
      answerProcessingTasks.clear()
    },

    setMediaMode(mode) {
      this.mediaMode = mode === 'video' ? 'video' : 'audio'
    }
  }
})
