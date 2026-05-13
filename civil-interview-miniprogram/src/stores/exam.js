import { defineStore } from 'pinia'
import { startExam, uploadRecording, completeExam } from '../api/exam'
import { evaluateAnswer, transcribeAudio } from '../api/scoring'
import { normalizeResult } from '../utils/scoring'

const EMPTY_TRANSCRIPT_TEXT = '未作答'

function buildZeroScoreResult() {
  return normalizeResult({
    totalScore: 0,
    maxScore: 100,
    grade: 'D',
    dimensions: [
      { name: '综合分析', key: 'analysis', score: 0, maxScore: 20 },
      { name: '实务落地', key: 'practical', score: 0, maxScore: 20 },
      { name: '应急应变', key: 'emergency', score: 0, maxScore: 15 },
      { name: '法治思维', key: 'legal', score: 0, maxScore: 15 },
      { name: '逻辑结构', key: 'logic', score: 0, maxScore: 15 },
      { name: '语言表达', key: 'expression', score: 0, maxScore: 15 }
    ],
    aiComment: '本题未提交有效作答内容，按空答案记 0 分。',
    scoringMode: 'empty_zero'
  })
}

async function evaluateEmptyAnswer(questionId, examId) {
  return buildZeroScoreResult()
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

    async submitCurrentAnswer({ text = '', filePath = '', mediaType = 'audio' } = {}) {
      const question = this.currentQuestion
      if (!question) throw new Error('当前题目不存在')
      if (!this.examId) throw new Error('考试会话不存在，请重新开始')

      this.loading = true
      try {
        let transcript = String(text || '').trim()
        if (filePath) {
          await uploadRecording(this.examId, question.id, filePath, { mediaType })
          if (!transcript) {
            const transcribeResult = await transcribeAudio(filePath, { mediaType })
            transcript = String(transcribeResult?.transcript || '').trim()
          }
        }

        const result = transcript
          ? normalizeResult(await evaluateAnswer({
            questionId: question.id,
            transcript,
            examId: this.examId
          }))
          : await evaluateEmptyAnswer(question.id, this.examId)
        const resolvedTranscript = transcript || EMPTY_TRANSCRIPT_TEXT

        const answer = {
          examId: this.examId,
          questionId: question.id,
          questionStem: question.stem,
          questionIndex: this.currentIndex,
          transcript: resolvedTranscript,
          scoringResult: result,
          submittedAt: new Date().toISOString()
        }
        this.answers = [
          ...this.answers.filter((item) => item.questionIndex !== this.currentIndex),
          answer
        ].sort((a, b) => a.questionIndex - b.questionIndex)
        this.latestResult = result
        this.latestTranscript = resolvedTranscript
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
