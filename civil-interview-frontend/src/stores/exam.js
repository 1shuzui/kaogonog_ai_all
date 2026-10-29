/**
 * PC 考试状态仓库，保存当前考试、题目队列、全真模拟模式、答题媒体状态和结果跳转所需上下文。
 *
 * 考场组件需要跨录音、上传、评分和结果页共享状态，所以不要把这些数据散放在组件局部变量里。
 * 作答阶段只管理题目和媒体，不在 store 中提前显示评分后才有的分数或诊断。
 *
 * @param 无；actions 接收抽题参数、考试 ID、媒体提交内容或结果保存数据。
 * @return 导出 Pinia store，供准备页、考场页和结果页共享考试流程状态。
 * @raises Error: 创建考试、上传答案、完成考试或评分失败时由 action 抛给页面处理。
 */
import { defineStore } from 'pinia'
import { EXAM_STATUS } from '@/utils/constants'
import { startExam, uploadRecording, completeExam } from '@/api/exam'
import { transcribeAudio, evaluateAnswer } from '@/api/scoring'
import {
  getScoringUnavailableMessage,
  isQuestionIdScoringSupported,
  normalizeScoringErrorMessage
} from '@/utils/scoringSupport'

const answerProcessingTasks = new Map()
const examFinishingTasks = new Map()
const EMPTY_TRANSCRIPT_TEXT = '未作答'

function currentSession() {
  return typeof localStorage === 'undefined' ? null : localStorage.getItem('token')
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

function buildZeroScoreResult() {
  return {
    totalScore: 0,
    maxScore: 100,
    grade: 'D',
    dimensions: [
      { name: '综合分析', key: 'analysis', score: 0, maxScore: 20, lostReasons: [] },
      { name: '实务落地', key: 'practical', score: 0, maxScore: 20, lostReasons: [] },
      { name: '应急应变', key: 'emergency', score: 0, maxScore: 15, lostReasons: [] },
      { name: '行政思维', key: 'legal', score: 0, maxScore: 15, lostReasons: [] },
      { name: '逻辑结构', key: 'logic', score: 0, maxScore: 15, lostReasons: [] },
      { name: '语言表达', key: 'expression', score: 0, maxScore: 15, lostReasons: [] }
    ],
    aiComment: '本题未提交有效作答内容，按空答案记 0 分。',
    scoringMode: 'empty_zero'
  }
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

async function evaluateEmptyAnswer(questionId, examId) {
  if (!examId) return buildZeroScoreResult()
  return evaluateScoredAnswer({
      questionId,
      transcript: '',
      examId
    })
}

function assertQuestionScoringSupported(questionId) {
  if (isQuestionIdScoringSupported(questionId)) return

  throw new Error(getScoringUnavailableMessage(1))
}

function normalizeExamError(error) {
  const message = normalizeScoringErrorMessage(error?.normalizedMessage || error?.message || '')
  if (message && message !== error?.message) {
    error.message = message
  }
  return error
}

export const useExamStore = defineStore('exam', {
  state: () => ({
    status: EXAM_STATUS.IDLE,
    examId: null,
    questionList: [],
    currentIndex: 0,
    recordingBlob: null,
    transcript: '',
    scoringResult: null,
    answers: [],
    archivedAnswers: [],
    // A fresh object also invalidates in-flight work after Pinia $reset with the same token.
    answerScope: { token: currentSession() },
    deviceReady: false,
    videoEnabled: true,
    mediaStream: null,
    fullExamMode: false,
    examStartTime: null,
    examElapsed: 0,
    submitStep: '',
    finishError: ''
  }),

  getters: {
    /** All non-completed answers in this login session, oldest exam first; original reactive objects. */
    pendingAnswers(state) {
      if (state.answerScope.token !== currentSession()) return []
      return [...state.archivedAnswers, ...state.answers].filter((answer) => answer.processingStatus !== 'completed')
    },
    currentQuestion(state) {
      return state.questionList[state.currentIndex] || null
    },
    currentAnswer(state) {
      return state.answers.find((item) => item.questionIndex === state.currentIndex) || null
    },
    currentQuestionNumber(state) {
      return state.currentIndex + 1
    },
    totalQuestions(state) {
      return state.questionList.length
    },
    isLastQuestion(state) {
      return state.currentIndex >= state.questionList.length - 1
    },
    examProgress(state) {
      if (!state.questionList.length) return 0
      return Math.round((state.answers.length / state.questionList.length) * 100)
    },
    overallScore(state) {
      const scoredAnswers = state.answers.filter((item) => item.scoringResult)
      if (!scoredAnswers.length) return 0
      const total = scoredAnswers.reduce((sum, item) => sum + (item.scoringResult?.totalScore || 0), 0)
      return Math.round(total / scoredAnswers.length)
    },
    submitStepText(state) {
      const map = {
        uploading: '正在上传本题录音...',
        transcribing: '正在转写本题作答...',
        scoring: '正在评分本题...',
        batchScoring: '正在对已完成题目统一评分...'
      }
      return map[state.submitStep] || '处理中...'
    }
  },

  actions: {
    ensureAnswerSession() {
      if (this.answerScope.token !== currentSession()) this.exitExam()
    },

    /** Session-local original answer objects, including completed archives until reset; no request. */
    getAnswersForExam(examId) {
      this.ensureAnswerSession()
      if (!examId) return []
      return [...this.archivedAnswers, ...this.answers]
        .filter((answer) => answer.examId === examId)
        .sort((a, b) => a.questionIndex - b.questionIndex)
    },

    async initExam(questions, fullExamMode = false, practiceMode = 'free') {
      this.ensureAnswerSession()
      const scope = this.answerScope
      const result = await startExam(questions.map((q) => q.id), fullExamMode ? 'fullExam' : practiceMode)
      assertAnswerScope(this, scope)
      // Commit the transition only after server success. Keep the original task-owned objects.
      // Keep completed results until session reset so watched old-exam result pages never lose them.
      const pendingExamIds = new Set(this.pendingAnswers.map((answer) => answer.examId))
      this.archivedAnswers = [...this.archivedAnswers, ...this.answers]
      // Retain the whole exam's media if even one answer needs processing/retry.
      for (const answer of this.archivedAnswers) {
        if (!pendingExamIds.has(answer.examId)) answer.recordingBlob = null
      }
      this.questionList = questions
      this.currentIndex = 0
      this.answers = []
      this.status = EXAM_STATUS.IDLE
      this.recordingBlob = null
      this.transcript = ''
      this.scoringResult = null
      this.fullExamMode = fullExamMode
      this.examStartTime = fullExamMode ? Date.now() : null
      this.examElapsed = 0
      this.submitStep = ''
      this.finishError = ''
      this.examId = result.examId
    },

    startPreparing() {
      this.status = EXAM_STATUS.PREPARING
      this.recordingBlob = null
      this.transcript = ''
      this.scoringResult = null
    },

    startAnswering() {
      this.status = EXAM_STATUS.ANSWERING
    },

    async submitAnswer(blob, transcript = '') {
      this.ensureAnswerSession()
      transcript = String(transcript || '').trim()
      if (transcript.length > 5000) throw new Error('文字作答最多 5000 字')
      const question = this.currentQuestion
      if (!question) {
        throw new Error('当前题目不存在')
      }

      const questionId = question.id
      const questionIndex = this.currentIndex
      const existing = this.answers.find((item) => item.examId === this.examId && item.questionIndex === questionIndex)
      if (existing && existing.processingStatus !== 'failed') return existing

      this.status = EXAM_STATUS.SUBMITTING
      this.recordingBlob = blob
      this.submitStep = 'uploading'

      try {
        assertQuestionScoringSupported(questionId)
        this.answers = this.answers.filter((item) => item.questionIndex !== questionIndex)
        this.answers.push({
          examId: this.examId,
          questionId,
          questionIndex,
          questionStem: question.stem || '',
          province: question.province,
          recordingBlob: blob,
          transcript,
          scoringResult: null,
          submittedAt: new Date().toISOString(),
          processingStatus: 'queued',
          processingError: ''
        })
        const queuedAnswer = this.answers[this.answers.length - 1]
        this.transcript = ''
        this.scoringResult = null

        this.status = EXAM_STATUS.COMPLETED
        this.submitStep = ''
        this.queueExamAnswerProcessing(queuedAnswer)
        return queuedAnswer
      } catch (err) {
        this.status = EXAM_STATUS.ANSWERING
        this.submitStep = ''
        throw normalizeExamError(err)
      }
    },

    queueExamAnswerProcessing(answer) {
      this.ensureAnswerSession()
      if (!ownsAnswer(this, answer)) return Promise.resolve(null)
      const taskKey = `${answer.examId}:${answer.questionIndex}`
      if (answerProcessingTasks.has(taskKey)) return answerProcessingTasks.get(taskKey)
      answer.processingError = ''
      const task = this.processExamAnswer(answer, currentSession())
        .catch((error) => {
          const normalizedError = normalizeExamError(error)
          answer.processingStatus = 'failed'
          answer.processingError = error?.message || '未知错误'
          answer.processingError = normalizedError.message || answer.processingError
          return answer
        })
        .finally(() => {
          if (answerProcessingTasks.get(taskKey) === task) answerProcessingTasks.delete(taskKey)
        })

      answerProcessingTasks.set(taskKey, task)
      return task
    },

    async processExamAnswer(answer, session = currentSession()) {
      const scope = this.answerScope
      const checkSession = () => {
        assertAnswerScope(this, scope, answer)
        assertSession(session)
      }
      checkSession()
      const answerExamId = answer.examId || this.examId
      let transcript = String(answer.transcript || '').trim()
      if ((!answer.recordingBlob || answer.recordingBlob.size <= 0) && !transcript) {
        assertQuestionScoringSupported(answer.questionId)
        const result = await evaluateEmptyAnswer(answer.questionId, answerExamId)
        checkSession()
        answer.recordingBlob = null
        answer.transcript = EMPTY_TRANSCRIPT_TEXT
        answer.scoringResult = result
        answer.processingStatus = 'completed'
        if (this.examId === answerExamId && this.currentIndex === answer.questionIndex) {
          this.transcript = EMPTY_TRANSCRIPT_TEXT
          this.scoringResult = result
        }
        return answer
      }

      answer.processingError = ''
      if (!transcript) {
        answer.processingStatus = 'uploading'
        if (!answer.mediaUploaded) {
          const uploaded = await uploadRecording(answerExamId, answer.questionId, answer.recordingBlob)
          checkSession()
          answer.mediaUploaded = true
          answer.mediaUrl = uploaded?.fileUrl || ''
          answer.mediaType = uploaded?.mediaType || answer.recordingBlob?.type || ''
        }
        checkSession()
        answer.processingStatus = 'transcribing'
        const response = await transcribeAudio(answer.recordingBlob, {
          questionId: answer.questionId,
          examId: answerExamId
        })
        checkSession()
        transcript = String(response?.transcript || '').trim()
        const asrStatus = response?.asrMeta?.status || response?.status || ''
        if (!transcript || ['too_short', 'silent_audio', 'empty_audio', 'no_speech', 'asr_unavailable', 'funasr_error', 'error', 'timeout'].includes(asrStatus)
          || /未能识别出有效语音|未配置真实语音转写服务|无法生成可靠文字稿/.test(transcript)) {
          throw new Error(response?.message || '未取得有效文字稿，录音已保留，可在结果页重试')
        }
        answer.transcript = transcript
      }

      if (this.examId === answerExamId && this.currentIndex === answer.questionIndex) {
        this.transcript = transcript
      }

      answer.processingStatus = 'scoring'
      checkSession()
      assertQuestionScoringSupported(answer.questionId)
      const result = await evaluateScoredAnswer({
        questionId: answer.questionId,
        transcript,
        examId: answerExamId
      })
      checkSession()
      const resolvedTranscript = result?.transcript || transcript
      answer.transcript = resolvedTranscript
      answer.scoringResult = result
      answer.processingStatus = 'completed'

      if (this.examId === answerExamId && this.currentIndex === answer.questionIndex) {
        this.transcript = resolvedTranscript
        this.scoringResult = result
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
      return this.queueExamAnswerProcessing(answer)
    },

    finish() {
      this.ensureAnswerSession()
      const examId = this.examId
      if (!examId) return Promise.resolve()
      if (examFinishingTasks.has(examId)) return examFinishingTasks.get(examId)
      const scope = this.answerScope
      this.finishError = ''
      // Freeze completion time now. Scoring later refreshes history without extending the exam.
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

    async evaluatePendingAnswers() {
      await this.waitForPendingProcessing()

      const incompleteAnswers = this.answers.filter((item) => !item.transcript && item.recordingBlob)

      if (this.fullExamMode && incompleteAnswers.length) {
        const previousStatus = this.status
        this.status = EXAM_STATUS.SUBMITTING
        this.submitStep = 'batchScoring'

        try {
          for (const answer of incompleteAnswers) {
            await this.processExamAnswer(answer)
          }
        } catch (err) {
          this.status = previousStatus
          this.submitStep = ''
          throw err
        }
      }

      const finalPendingAnswers = this.answers.filter((item) => item.transcript && !item.scoringResult)
      if (!finalPendingAnswers.length) {
        const current = this.answers.find((item) => item.questionIndex === this.currentIndex)
        this.scoringResult = current?.scoringResult || null
        this.submitStep = ''
        return this.answers
      }

      const previousStatus = this.status
      this.status = EXAM_STATUS.SUBMITTING
      this.submitStep = 'batchScoring'

      try {
        for (const answer of finalPendingAnswers) {
          assertQuestionScoringSupported(answer.questionId)
          const result = await evaluateScoredAnswer({
            questionId: answer.questionId,
            transcript: answer.transcript,
            examId: answer.examId || this.examId
          })
          answer.scoringResult = result
          answer.processingStatus = 'completed'
        }

        const current = this.answers.find((item) => item.questionIndex === this.currentIndex)
        this.scoringResult = current?.scoringResult || this.answers[this.answers.length - 1]?.scoringResult || null
        this.status = EXAM_STATUS.COMPLETED
        this.submitStep = ''
        return this.answers
      } catch (err) {
        this.status = previousStatus
        this.submitStep = ''
        throw normalizeExamError(err)
      }
    },

    syncQuestionViewState() {
      const answer = this.answers.find((item) => item.questionIndex === this.currentIndex)

      if (answer) {
        this.status = EXAM_STATUS.COMPLETED
        this.recordingBlob = answer.recordingBlob || null
        this.transcript = answer.transcript || ''
        this.scoringResult = answer.scoringResult || null
        this.submitStep = ''
        return
      }

      this.status = EXAM_STATUS.IDLE
      this.recordingBlob = null
      this.transcript = ''
      this.scoringResult = null
      this.submitStep = ''
    },

    goToQuestion(index) {
      if (!this.questionList.length) return
      const nextIndex = Math.min(Math.max(Number(index) || 0, 0), this.questionList.length - 1)
      this.currentIndex = nextIndex
      this.syncQuestionViewState()
    },

    previousQuestion() {
      if (this.currentIndex <= 0) return
      this.goToQuestion(this.currentIndex - 1)
    },

    nextQuestion() {
      if (!this.isLastQuestion) {
        this.goToQuestion(this.currentIndex + 1)
      } else {
        this.syncQuestionViewState()
      }
    },

    resetCurrentQuestionState() {
      if (!this.currentAnswer) {
        this.status = EXAM_STATUS.IDLE
        this.recordingBlob = null
        this.transcript = ''
        this.scoringResult = null
        this.submitStep = ''
      }
    },

    exitExam() {
      this.destroyStream()
      this.status = EXAM_STATUS.IDLE
      this.examId = null
      this.questionList = []
      this.currentIndex = 0
      this.answers = []
      this.archivedAnswers = []
      this.answerScope = { token: currentSession() }
      this.recordingBlob = null
      this.transcript = ''
      this.scoringResult = null
      this.fullExamMode = false
      this.examStartTime = null
      this.examElapsed = 0
      this.submitStep = ''
      this.finishError = ''
    },

    setDeviceReady(ready) {
      this.deviceReady = ready
    },

    setVideoEnabled(enabled) {
      this.videoEnabled = enabled
    },

    storeStream(stream) {
      this.mediaStream = stream
    },

    consumeStream() {
      const stream = this.mediaStream
      this.mediaStream = null
      return stream
    },

    destroyStream() {
      if (this.mediaStream) {
        this.mediaStream.getTracks().forEach(t => t.stop())
        this.mediaStream = null
      }
    }
  }
})
