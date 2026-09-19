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
const examFinishingTasks = new Map()

function currentSession() {
  return typeof uni === 'undefined' ? null : uni.getStorageSync('token')
}

function assertSession(session) {
  if (currentSession() !== session) {
    throw Object.assign(new Error('账号已切换，请在原账号的练习记录中继续处理'), { code: 'STALE_SESSION' })
  }
}

function ownsAnswer(store, answer) {
  return store.answers.includes(answer) || store.archivedAnswers.includes(answer)
}

function assertAnswerScope(store, scope, answer = null) {
  store.ensureAnswerSession()
  assertSession(scope.token)
  if (store.answerScope !== scope || (answer && !ownsAnswer(store, answer))) {
    throw Object.assign(new Error('考试任务已清理，请重新开始'), { code: 'STALE_SESSION' })
  }
}

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

async function transcribeAudioWithRetry(filePath, options = {}, checkOwnership = () => {}) {
  const session = currentSession()
  let lastResult = null
  let lastError = null
  for (let attempt = 0; attempt < 2; attempt += 1) {
    checkOwnership()
    assertSession(session)
    try {
      const result = await transcribeAudio(filePath, options)
      lastResult = { ...result, retryCount: attempt }
      if (!shouldRetryTranscribeResult(result)) return lastResult
    } catch (error) {
      if (error?.code === 'STALE_SESSION') throw error
      lastError = error
    }
  }
  if (lastError) {
    throw buildAsrError(lastError?.message || '语音服务异常，请稍后重试', {}, 'asr_unavailable')
  }
  return lastResult || {}
}

async function evaluateScoredAnswer(payload) {
  const result = await evaluateAnswer(payload)
  const score = result?.totalScore ?? result?.score
  // Validate before normalization can turn a missing score into an apparent zero.
  const numeric = typeof score === 'number' || (typeof score === 'string' && score.trim() !== '')
  if (!numeric || !Number.isFinite(Number(score))) {
    throw Object.assign(new Error('点评未返回有效分数，作答已保留，请重试'), { code: 'INVALID_SCORING_RESULT' })
  }
  return result
}

async function evaluateEmptyAnswer(questionId, examId, options = {}) {
  const answerMeta = options.answerMeta || {}
  if (!examId) return buildZeroScoreResult({ ...options, ...answerMeta })
  return mergeAnswerMetaIntoResult(await evaluateScoredAnswer({
      questionId,
      transcript: '',
      examId,
      answerMeta
    }), answerMeta)
}

export const useExamStore = defineStore('exam', {
  state: () => ({
    examId: '',
    questions: [],
    currentIndex: 0,
    answers: [],
    archivedAnswers: [],
    answerScope: { token: currentSession() },
    latestResult: null,
    latestTranscript: '',
    loading: false,
    source: '',
    mediaMode: 'audio',
    finishError: ''
  }),

  getters: {
    /** All non-completed answers in this login session, oldest exam first; original reactive objects. */
    pendingAnswers(state) {
      if (state.answerScope.token !== currentSession()) return []
      return [...state.archivedAnswers, ...state.answers].filter((answer) => answer.processingStatus !== 'completed')
    },
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
    ensureAnswerSession() {
      if (this.answerScope.token !== currentSession()) this.reset()
    },

    /** Session-local original answer objects, including completed archives until reset; no request. */
    getAnswersForExam(examId) {
      this.ensureAnswerSession()
      if (!examId) return []
      return [...this.archivedAnswers, ...this.answers]
        .filter((answer) => answer.examId === examId)
        .sort((a, b) => a.questionIndex - b.questionIndex)
    },

    async startFromQuestions(questions = [], source = '') {
      this.ensureAnswerSession()
      const scope = this.answerScope
      const list = Array.isArray(questions) ? questions.filter(Boolean) : []
      if (!list.length) throw new Error('暂无可用题目')
      const practiceMode = source.startsWith('training') ? 'training' : ['fullExam', 'targeted', 'trial'].includes(source) ? source : 'free'
      const response = await startExam(list.map((item) => item.id), practiceMode)
      assertAnswerScope(this, scope)
      // Archive only after server success; task maps are released by their own finally handlers.
      // Keep completed results until session reset so watched old-exam result pages never lose them.
      const pendingExamIds = new Set(this.pendingAnswers.map((answer) => answer.examId))
      this.archivedAnswers = [...this.archivedAnswers, ...this.answers]
      // Retain the whole exam's media if even one answer needs processing/retry.
      for (const answer of this.archivedAnswers) {
        if (!pendingExamIds.has(answer.examId)) {
          answer.filePath = ''
          answer.audioFilePath = ''
        }
      }
      this.examId = response.examId
      this.questions = list
      this.currentIndex = 0
      this.answers = []
      this.latestResult = null
      this.latestTranscript = ''
      this.source = source
      this.finishError = ''
      return response
    },

    async submitCurrentAnswer({
      filePath = '',
      transcript = '',
      mediaType = 'audio',
      audioFilePath = '',
      skipConfirmed = false,
      skipReason = '',
      timingMeta = null,
      waitForProcessing = true
    } = {}) {
      this.ensureAnswerSession()
      const question = this.currentQuestion
      if (!question) throw new Error('当前题目不存在')
      if (!this.examId) throw new Error('考试会话不存在，请重新开始')
      transcript = String(transcript || '').trim()
      if (transcript.length > 5000) throw new Error('文字作答最多 5000 字')
      const existing = this.answers.find((item) => item.examId === this.examId && item.questionIndex === this.currentIndex)
      if (existing && existing.processingStatus !== 'failed') {
        if (waitForProcessing !== false) await answerProcessingTasks.get(`${existing.examId}:${existing.questionIndex}`)
        return existing
      }

      this.loading = true
      try {
        const hasAnswerPayload = !!filePath || !!transcript

        if (!hasAnswerPayload) {
          if (!skipConfirmed) throw new Error('当前没有录音或录像，请先录制后提交')
          skipReason = skipReason || 'user_confirmed_skip'
        }

        const previousAnswer = this.answers.find((item) => (
          item.examId === this.examId && item.questionId === question.id
          && item.questionIndex === this.currentIndex && item.filePath === filePath
          && item.processingStatus === 'failed' && !isPlaceholderTranscript(item.transcript)
        ))
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
          skipReason,
          transcript: transcript || previousAnswer?.transcript || '',
          asrMeta: previousAnswer?.asrMeta || {},
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
        this.latestTranscript = answer.transcript
        // Read back the reactive proxy: background mutations must update the result page.
        const queuedAnswer = this.answers.find((item) => item.questionIndex === answer.questionIndex)
        const task = this.queueAnswerProcessing(queuedAnswer)
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
        return queuedAnswer
      } finally {
        this.loading = false
      }
    },

    queueAnswerProcessing(answer) {
      this.ensureAnswerSession()
      if (!ownsAnswer(this, answer)) return Promise.resolve(null)
      const taskKey = `${answer.examId}:${answer.questionIndex}`
      if (answerProcessingTasks.has(taskKey)) return answerProcessingTasks.get(taskKey)
      answer.processingError = ''
      const task = this.processAnswer(answer, currentSession())
        .catch((error) => {
          answer.processingStatus = 'failed'
          answer.processingError = answer.transcript
            ? '文字稿已保留，点评暂未完成。可在结果页重试，无需重新录音。'
            : error?.message || '评分失败'
          answer.asrFailureType = error?.asrFailureType || ''
          answer.asrMessage = error?.asrMessage || ''
          answer.userInvalid = error?.userInvalid === true
          answer.serviceFailure = error?.serviceFailure === true
          return answer
        })
        .finally(() => {
          if (answerProcessingTasks.get(taskKey) === task) answerProcessingTasks.delete(taskKey)
        })
      answerProcessingTasks.set(taskKey, task)
      return task
    },

    async processAnswer(answer, session = currentSession()) {
      const scope = this.answerScope
      const checkSession = () => {
        assertAnswerScope(this, scope, answer)
        assertSession(session)
      }
      checkSession()
      let transcript = isPlaceholderTranscript(answer.transcript) ? '' : String(answer.transcript).trim()
      const mediaType = answer.mediaType || 'audio'
      answer.processingStatus = answer.filePath ? 'uploading' : 'scoring'

      if (answer.filePath && !transcript) {
        const uploadMedia = await prepareMediaForUpload(answer.filePath, mediaType)
        checkSession()
        const transcriptionMedia = mediaType === 'video' && answer.audioFilePath
          ? await prepareMediaForUpload(answer.audioFilePath, 'audio')
          : uploadMedia

        checkSession()
        if (!answer.mediaUploaded) {
          await uploadRecording(answer.examId, answer.questionId, uploadMedia.filePath, {
          mediaType,
          source: uploadMedia.compressed
            ? `miniapp_${mediaType}_recording_compressed`
            : `miniapp_${mediaType}_recording`
          })
          checkSession()
          answer.mediaUploaded = true
        }
        checkSession()
        if (!transcript) {
          answer.processingStatus = 'transcribing'
          const transcribeResult = await transcribeAudioWithRetry(transcriptionMedia.filePath, {
            mediaType: transcriptionMedia.mediaType || mediaType,
            questionId: answer.questionId,
            examId: answer.examId
          }, checkSession)
          checkSession()
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
          answer.transcript = transcript
          if (this.examId === answer.examId && this.currentIndex === answer.questionIndex) {
            this.latestTranscript = transcript
          }
        }
      }

      answer.processingStatus = 'scoring'
      checkSession()
      const answerMeta = {
        ...(answer.skipReason ? { skipReason: answer.skipReason } : {}),
        ...(answer.answerTiming ? { answerTiming: answer.answerTiming } : {}),
        ...(answer.asrMeta?.status ? { asrStatus: answer.asrMeta.status } : {}),
        ...(answer.asrMeta?.message ? { asrMessage: answer.asrMeta.message } : {})
      }
      const result = transcript
        ? mergeAnswerMetaIntoResult(await evaluateScoredAnswer({
          questionId: answer.questionId,
          transcript,
          examId: answer.examId,
          answerMeta
        }), answerMeta)
        : await evaluateEmptyAnswer(answer.questionId, answer.examId, { answerMeta })

      checkSession()

      answer.transcript = transcript || EMPTY_TRANSCRIPT_TEXT
      answer.scoringResult = result
      answer.processingStatus = 'completed'

      if (this.examId === answer.examId && this.currentIndex === answer.questionIndex) {
        this.latestResult = result
        this.latestTranscript = answer.transcript
      }

      return answer
    },

    async waitForPendingProcessing(examId = this.examId) {
      if (!answerProcessingTasks.size) return
      await Promise.allSettled(Array.from(answerProcessingTasks.entries())
        .filter(([key]) => key.startsWith(`${examId}:`)).map(([, task]) => task))
    },

    /** Retry a task returned by this store, including archived exams. Invalid/stale objects resolve null. */
    retryAnswer(answer) {
      this.ensureAnswerSession()
      if (!ownsAnswer(this, answer)) return Promise.resolve(null)
      if (answer.processingStatus === 'completed') return Promise.resolve(answer)
      return this.queueAnswerProcessing(answer)
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

    finish() {
      this.ensureAnswerSession()
      const examId = this.examId
      if (!examId) return Promise.resolve()
      if (examFinishingTasks.has(examId)) return examFinishingTasks.get(examId)
      const scope = this.answerScope
      this.finishError = ''
      const firstSave = completeExam(examId).catch(() => null)
      const pending = this.waitForPendingProcessing(examId)
      const task = Promise.all([firstSave, pending]).then(() => {
        assertAnswerScope(this, scope)
        return completeExam(examId)
      }).catch((error) => {
        if (this.answerScope === scope && this.examId === examId) this.finishError = error?.message || '练习记录同步失败，请重试'
      }).finally(() => examFinishingTasks.delete(examId))
      examFinishingTasks.set(examId, task)
      return task
    },

    reset() {
      this.examId = ''
      this.questions = []
      this.currentIndex = 0
      this.answers = []
      this.archivedAnswers = []
      this.answerScope = { token: currentSession() }
      this.latestResult = null
      this.latestTranscript = ''
      this.loading = false
      this.source = ''
      this.mediaMode = 'audio'
      this.finishError = ''
    },

    setMediaMode(mode) {
      this.mediaMode = mode === 'video' ? 'video' : 'audio'
    }
  }
})
