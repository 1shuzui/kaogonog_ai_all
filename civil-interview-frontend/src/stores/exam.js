import { defineStore } from 'pinia'
import { EXAM_STATUS } from '@/utils/constants'
import { startExam, uploadRecording } from '@/api/exam'
import { transcribeAudio, evaluateAnswer } from '@/api/scoring'

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
    // 模拟面试模式
    mockMode: false,
    examStartTime: null,
    examElapsed: 0,
    // 提交步骤提示
    submitStep: '',  // '' | 'uploading' | 'transcribing' | 'scoring'
  }),

  getters: {
    currentQuestion(state) {
      return state.questionList[state.currentIndex] || null
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
      if (!state.answers.length) return 0
      const total = state.answers.reduce((sum, a) => sum + (a.scoringResult?.totalScore || 0), 0)
      return Math.round(total / state.answers.length)
    },
    submitStepText(state) {
      const map = {
        uploading: '正在上传录音…',
        transcribing: '正在语音转文字…',
        scoring: 'AI 正在评分，请稍候…'
      }
      return map[state.submitStep] || '处理中…'
    }
  },

  actions: {
    async initExam(questions, mockMode = false) {
      this.questionList = questions
      this.currentIndex = 0
      this.answers = []
      this.status = EXAM_STATUS.IDLE
      this.mockMode = mockMode
      this.examStartTime = mockMode ? Date.now() : null
      this.examElapsed = 0
      const result = await startExam(questions.map(q => q.id))
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
      this.status = EXAM_STATUS.SUBMITTING
      this.recordingBlob = blob
      this.submitStep = 'uploading'

      try {
        // 上传录制文件
        await uploadRecording(this.examId, blob)

        // 语音转文字
        this.submitStep = 'transcribing'
        const { transcript } = await transcribeAudio(blob)
        this.transcript = transcript

        // AI 评分
        this.submitStep = 'scoring'
        const result = await evaluateAnswer({
          examId: this.examId,
          questionId: this.currentQuestion.id,
          transcript
        })
        this.scoringResult = result

        // 保存答案
        this.answers.push({
          questionId: this.currentQuestion.id,
          questionIndex: this.currentIndex,
          recordingBlob: blob,
          transcript,
          scoringResult: result,
          submittedAt: new Date().toISOString()
        })

        this.status = EXAM_STATUS.COMPLETED
        this.submitStep = ''
      } catch (err) {
        this.status = EXAM_STATUS.ANSWERING
        this.submitStep = ''
        throw err
      }
    },

    nextQuestion() {
      if (!this.isLastQuestion) {
        this.currentIndex++
        this.status = EXAM_STATUS.IDLE
        this.recordingBlob = null
        this.transcript = ''
        this.scoringResult = null
      }
    },

    exitExam() {
      this.status = EXAM_STATUS.IDLE
      this.examId = null
      this.questionList = []
      this.currentIndex = 0
      this.recordingBlob = null
      this.transcript = ''
      this.scoringResult = null
      this.mockMode = false
      this.examStartTime = null
      this.examElapsed = 0
      this.submitStep = ''
    },

    setDeviceReady(ready) {
      this.deviceReady = ready
    }
  }
})
