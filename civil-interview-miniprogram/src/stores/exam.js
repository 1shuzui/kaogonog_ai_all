import { defineStore } from 'pinia'
import { startExam, uploadRecording, completeExam } from '../api/exam'
import { evaluateAnswer, transcribeAudio } from '../api/scoring'
import { normalizeResult } from '../utils/scoring'

export const useExamStore = defineStore('exam', {
  state: () => ({
    examId: '',
    questions: [],
    currentIndex: 0,
    answers: [],
    latestResult: null,
    latestTranscript: '',
    loading: false,
    source: ''
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
      return response
    },

    async submitCurrentAnswer({ text = '', filePath = '' } = {}) {
      const question = this.currentQuestion
      if (!question) throw new Error('当前题目不存在')
      if (!this.examId) throw new Error('考试会话不存在，请重新开始')

      this.loading = true
      try {
        let transcript = String(text || '').trim()
        if (filePath) {
          await uploadRecording(this.examId, question.id, filePath)
          if (!transcript) {
            const transcribeResult = await transcribeAudio(filePath)
            transcript = String(transcribeResult?.transcript || '').trim()
          }
        }

        if (!transcript) {
          throw new Error('请先录音或输入文字作答')
        }

        const result = normalizeResult(await evaluateAnswer({
          questionId: question.id,
          transcript,
          examId: this.examId
        }))

        const answer = {
          examId: this.examId,
          questionId: question.id,
          questionStem: question.stem,
          questionIndex: this.currentIndex,
          transcript,
          scoringResult: result,
          submittedAt: new Date().toISOString()
        }
        this.answers = [
          ...this.answers.filter((item) => item.questionIndex !== this.currentIndex),
          answer
        ].sort((a, b) => a.questionIndex - b.questionIndex)
        this.latestResult = result
        this.latestTranscript = transcript
        return answer
      } finally {
        this.loading = false
      }
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
    }
  }
})
