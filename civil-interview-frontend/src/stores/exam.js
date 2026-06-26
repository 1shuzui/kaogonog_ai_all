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
import { startExam, uploadRecording } from '@/api/exam'
import { transcribeAudio, evaluateAnswer } from '@/api/scoring'
import {
  getScoringUnavailableMessage,
  isQuestionIdScoringSupported,
  normalizeScoringErrorMessage
} from '@/utils/scoringSupport'

const answerProcessingTasks = new Map()
const EMPTY_TRANSCRIPT_TEXT = '未作答'

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

async function evaluateEmptyAnswer(questionId, examId) {
  if (!examId) return buildZeroScoreResult()
  try {
    return await evaluateAnswer({
      questionId,
      transcript: '',
      examId
    })
  } catch {
    return buildZeroScoreResult()
  }
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
    deviceReady: false,
    videoEnabled: true,
    mediaStream: null,
    fullExamMode: false,
    examStartTime: null,
    examElapsed: 0,
    submitStep: ''
  }),

  getters: {
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
    async initExam(questions, fullExamMode = false) {
      answerProcessingTasks.clear()
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
      const result = await startExam(questions.map((q) => q.id))
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

    async submitAnswer(blob) {
      const question = this.currentQuestion
      if (!question) {
        throw new Error('当前题目不存在')
      }

      const questionId = question.id
      const questionIndex = this.currentIndex

      this.status = EXAM_STATUS.SUBMITTING
      this.recordingBlob = blob
      this.submitStep = 'uploading'

      try {
        if (!blob || blob.size <= 0) {
          assertQuestionScoringSupported(questionId)
          const result = await evaluateEmptyAnswer(questionId, this.examId)
          this.scoringResult = result
          this.transcript = EMPTY_TRANSCRIPT_TEXT
          this.answers.push({
            examId: this.examId,
            questionId,
            questionIndex,
            recordingBlob: null,
            transcript: EMPTY_TRANSCRIPT_TEXT,
            scoringResult: result,
            submittedAt: new Date().toISOString(),
            processingStatus: 'completed'
          })
          this.status = EXAM_STATUS.COMPLETED
          this.submitStep = ''
          return this.answers[this.answers.length - 1]
        }

        this.answers.push({
          examId: this.examId,
          questionId,
          questionIndex,
          recordingBlob: blob,
          transcript: '',
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
      const task = this.processExamAnswer(answer)
        .catch((error) => {
          const normalizedError = normalizeExamError(error)
          answer.processingStatus = 'failed'
          answer.processingError = error?.message || '未知错误'
          throw normalizedError
        })
        .finally(() => {
          answerProcessingTasks.delete(answer.questionIndex)
        })

      answerProcessingTasks.set(answer.questionIndex, task)
      return task
    },

    async processExamAnswer(answer) {
      const answerExamId = answer.examId || this.examId
      if (!answer.recordingBlob || answer.recordingBlob.size <= 0) {
        assertQuestionScoringSupported(answer.questionId)
        const result = await evaluateEmptyAnswer(answer.questionId, answerExamId)
        answer.recordingBlob = null
        answer.transcript = EMPTY_TRANSCRIPT_TEXT
        answer.scoringResult = result
        answer.processingStatus = 'completed'
        this.transcript = EMPTY_TRANSCRIPT_TEXT
        this.scoringResult = result
        return answer
      }

      answer.processingError = ''
      answer.processingStatus = 'uploading'
      await uploadRecording(answerExamId, answer.questionId, answer.recordingBlob)

      answer.processingStatus = 'transcribing'
      const { transcript } = await transcribeAudio(answer.recordingBlob, { questionId: answer.questionId })
      answer.transcript = transcript

      if (this.examId === answerExamId && this.currentIndex === answer.questionIndex) {
        this.transcript = transcript
      }

      answer.processingStatus = 'scoring'
      assertQuestionScoringSupported(answer.questionId)
      const result = await evaluateAnswer({
        questionId: answer.questionId,
        transcript,
        examId: answerExamId
      })
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

    async waitForPendingProcessing() {
      if (!answerProcessingTasks.size) return
      await Promise.allSettled(Array.from(answerProcessingTasks.values()))
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
          const result = await evaluateAnswer({
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
      answerProcessingTasks.clear()
      this.destroyStream()
      this.status = EXAM_STATUS.IDLE
      this.examId = null
      this.questionList = []
      this.currentIndex = 0
      this.answers = []
      this.recordingBlob = null
      this.transcript = ''
      this.scoringResult = null
      this.fullExamMode = false
      this.examStartTime = null
      this.examElapsed = 0
      this.submitStep = ''
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
