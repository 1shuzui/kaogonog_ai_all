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
const answerProcessingTasks = new Map()

function buildZeroScoreResult() {
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
    aiComment: '本题未提交有效作答内容，按空答案记 0 分。',
    scoringMode: 'empty_zero'
  })
}

async function evaluateEmptyAnswer(questionId, examId) {
  if (!examId) return buildZeroScoreResult()
  try {
    return normalizeResult(await evaluateAnswer({
      questionId,
      transcript: '',
      examId
    }))
  } catch {
    return buildZeroScoreResult()
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

    async submitCurrentAnswer({ filePath = '', mediaType = 'audio', audioFilePath = '' } = {}) {
      const question = this.currentQuestion
      if (!question) throw new Error('当前题目不存在')
      if (!this.examId) throw new Error('考试会话不存在，请重新开始')

      this.loading = true
      try {
        const hasAnswerPayload = !!filePath

        if (!hasAnswerPayload) {
          const result = await evaluateEmptyAnswer(question.id, this.examId)
          const answer = {
            examId: this.examId,
            questionId: question.id,
            questionStem: question.stem,
            questionIndex: this.currentIndex,
            transcript: EMPTY_TRANSCRIPT_TEXT,
            scoringResult: result,
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
          filePath,
          mediaType,
          audioFilePath,
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
        this.queueAnswerProcessing(answer)
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
          const transcribeResult = await transcribeAudio(transcriptionMedia.filePath, {
            mediaType: transcriptionMedia.mediaType || mediaType
          })
          transcript = String(transcribeResult?.transcript || '').trim()
        }
      }

      answer.processingStatus = 'scoring'
      const result = transcript
        ? normalizeResult(await evaluateAnswer({
          questionId: answer.questionId,
          transcript,
          examId: answer.examId
        }))
        : await evaluateEmptyAnswer(answer.questionId, answer.examId)

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
