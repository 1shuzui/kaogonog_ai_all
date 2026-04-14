import { defineStore } from 'pinia'
import { EXAM_STATUS } from '@/utils/constants'
import { startExam, uploadRecording } from '@/api/exam'
import { transcribeAudio, evaluateAnswer } from '@/api/scoring'

const DEFAULT_PREP_TIME = 90
const DEFAULT_ANSWER_TIME = 180
const EXAM_SESSION_STORAGE_KEY = 'civil_exam_session'
const USERNAME_STORAGE_KEY = 'username'
const GUEST_STORAGE_SCOPE = 'guest'
const UNRELIABLE_TRANSCRIPT_MARKERS = [
  '未配置真实语音转写服务',
  '无法生成可靠文字稿',
  '未能识别出有效语音'
]

function resolveQuestionTime(time, preferred, defaultValue) {
  const normalizedPreferred = Number(preferred)
  if (Number.isFinite(normalizedPreferred) && normalizedPreferred > 0 && normalizedPreferred !== defaultValue) {
    return normalizedPreferred
  }
  const normalized = Number(time)
  if (!Number.isFinite(normalized) || normalized <= 0) {
    return defaultValue
  }
  return normalized
}

function getStorageScope(username = '') {
  try {
    const scope = String(username || localStorage.getItem(USERNAME_STORAGE_KEY) || GUEST_STORAGE_SCOPE).trim()
    return scope || GUEST_STORAGE_SCOPE
  } catch {
    return GUEST_STORAGE_SCOPE
  }
}

function getExamSessionStorageKey(username = '') {
  return `${EXAM_SESSION_STORAGE_KEY}:${getStorageScope(username)}`
}

function createDefaultState() {
  return {
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
    mockMode: false,
    examStartTime: null,
    examElapsed: 0,
    submitStep: ''
  }
}

function normalizeStoredAnswer(answer = {}) {
  return {
    questionId: answer.questionId || '',
    questionIndex: Number.isFinite(Number(answer.questionIndex)) ? Number(answer.questionIndex) : 0,
    questionStem: answer.questionStem || '',
    dimension: answer.dimension || '',
    prepTime: Number(answer.prepTime) || DEFAULT_PREP_TIME,
    answerTime: Number(answer.answerTime) || DEFAULT_ANSWER_TIME,
    recordingBlob: null,
    mediaUrl: answer.mediaUrl || '',
    mediaType: answer.mediaType || '',
    mediaFilename: answer.mediaFilename || '',
    mediaSource: answer.mediaSource || '',
    transcript: answer.transcript || '',
    scoringResult: answer.scoringResult && typeof answer.scoringResult === 'object' ? answer.scoringResult : null,
    submittedAt: answer.submittedAt || ''
  }
}

function normalizeStoredQuestion(question = {}) {
  return {
    ...question,
    prepTime: Number(question.prepTime) || DEFAULT_PREP_TIME,
    answerTime: Number(question.answerTime) || DEFAULT_ANSWER_TIME
  }
}

function buildPersistedSession(state) {
  if (!state.examId || !Array.isArray(state.questionList) || state.questionList.length === 0) {
    return null
  }

  return {
    status: state.status,
    examId: state.examId,
    questionList: state.questionList.map(normalizeStoredQuestion),
    currentIndex: Number.isFinite(Number(state.currentIndex)) ? Number(state.currentIndex) : 0,
    transcript: state.transcript || '',
    scoringResult: state.scoringResult && typeof state.scoringResult === 'object' ? state.scoringResult : null,
    answers: (state.answers || []).map(normalizeStoredAnswer),
    deviceReady: !!state.deviceReady,
    videoEnabled: typeof state.videoEnabled === 'boolean' ? state.videoEnabled : true,
    mockMode: !!state.mockMode,
    examStartTime: state.examStartTime || null,
    examElapsed: Number.isFinite(Number(state.examElapsed)) ? Number(state.examElapsed) : 0,
    submitStep: state.submitStep || ''
  }
}

function loadPersistedSession(username = '') {
  try {
    const raw = localStorage.getItem(getExamSessionStorageKey(username))
    if (!raw) return null

    const parsed = JSON.parse(raw)
    const snapshot = buildPersistedSession(parsed)
    if (!snapshot) return null

    const safeStatus = [
      EXAM_STATUS.PREPARING,
      EXAM_STATUS.ANSWERING,
      EXAM_STATUS.SUBMITTING
    ].includes(snapshot.status)
      ? EXAM_STATUS.IDLE
      : snapshot.status
    const currentIndex = Math.min(
      Math.max(Number(snapshot.currentIndex) || 0, 0),
      Math.max(snapshot.questionList.length - 1, 0)
    )
    const shouldRestoreCurrentResult = safeStatus === EXAM_STATUS.COMPLETED

    return {
      ...createDefaultState(),
      ...snapshot,
      status: safeStatus,
      questionList: snapshot.questionList.map(normalizeStoredQuestion),
      currentIndex,
      transcript: shouldRestoreCurrentResult ? snapshot.transcript : '',
      scoringResult: shouldRestoreCurrentResult ? snapshot.scoringResult : null,
      submitStep: '',
      answers: snapshot.answers.map(normalizeStoredAnswer),
      recordingBlob: null
    }
  } catch {
    return null
  }
}

function persistExamSession(state, username = '') {
  const snapshot = buildPersistedSession(state)
  try {
    if (!snapshot) {
      localStorage.removeItem(getExamSessionStorageKey(username))
      return
    }
    localStorage.setItem(getExamSessionStorageKey(username), JSON.stringify(snapshot))
  } catch {
    // ignore local storage failures
  }
}

export const useExamStore = defineStore('exam', {
  state: () => loadPersistedSession() || createDefaultState(),

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
    hasRecoverableSession(state) {
      return !!state.examId && state.questionList.length > 0
    },
    submitStepText(state) {
      const map = {
        uploading: '正在上传媒体…',
        transcribing: '正在语音转文字…',
        scoring: 'AI 正在评分，请稍候…'
      }
      return map[state.submitStep] || '处理中…'
    },
    submitProgressPercent(state) {
      const map = {
        uploading: 28,
        transcribing: 62,
        scoring: 90
      }
      return map[state.submitStep] || 0
    }
  },

  actions: {
    persistSession() {
      persistExamSession(this.$state)
    },

    restorePersistedSession(username = '') {
      const restored = loadPersistedSession(username)
      this.$patch(restored || createDefaultState())
    },

    clearPersistedSession(username = '') {
      try {
        localStorage.removeItem(getExamSessionStorageKey(username))
      } catch {
        // ignore local storage failures
      }
      this.$patch(createDefaultState())
    },

    async initExam(questions, mockMode = false, preferences = {}) {
      const preferredPrepTime = Number(preferences?.defaultPrepTime) || DEFAULT_PREP_TIME
      const preferredAnswerTime = Number(preferences?.defaultAnswerTime) || DEFAULT_ANSWER_TIME
      this.questionList = (questions || []).map(question => ({
        ...question,
        prepTime: resolveQuestionTime(question?.prepTime, preferredPrepTime, DEFAULT_PREP_TIME),
        answerTime: resolveQuestionTime(question?.answerTime, preferredAnswerTime, DEFAULT_ANSWER_TIME)
      }))
      this.currentIndex = 0
      this.answers = []
      this.status = EXAM_STATUS.IDLE
      this.mockMode = mockMode
      this.examStartTime = mockMode ? Date.now() : null
      this.examElapsed = 0
      this.submitStep = ''
      const result = await startExam(this.questionList.map(q => q.id))
      this.examId = result.examId
      this.persistSession()
    },

    startPreparing() {
      this.status = EXAM_STATUS.PREPARING
      this.recordingBlob = null
      this.transcript = ''
      this.scoringResult = null
      this.persistSession()
    },

    startAnswering() {
      this.status = EXAM_STATUS.ANSWERING
      this.persistSession()
    },

    async submitAnswer(blob, options = {}) {
      this.status = EXAM_STATUS.SUBMITTING
      this.recordingBlob = blob || null
      const skipUpload = !!options?.skipUpload
      this.submitStep = skipUpload ? 'scoring' : 'uploading'
      this.persistSession()

      try {
        let uploadResult = null
        if (!skipUpload) {
          if (!blob) {
            throw new Error('未获取到媒体文件，请重新作答，或改用文字 / 上传文件')
          }
          uploadResult = await uploadRecording(this.examId, blob, {
            questionId: this.currentQuestion.id,
            filename: options.mediaFileName,
            mediaType: options.mediaMimeType || blob?.type || '',
            source: options.mediaSource || 'live_recording'
          })
        }

        let transcript = String(options?.transcriptOverride || '').trim()
        if (!transcript) {
          if (skipUpload) {
            throw new Error('请输入文字答案后再提交')
          }
          this.submitStep = 'transcribing'
          const transcribeResult = await transcribeAudio(blob, {
            filename: options.mediaFileName
          })
          transcript = String(transcribeResult?.transcript || '').trim()
          if (UNRELIABLE_TRANSCRIPT_MARKERS.some(marker => transcript.includes(marker))) {
            throw new Error('未获取到可靠语音转写结果，请优先使用浏览器语音识别，或改用文字作答 / 上传 txt')
          }
        }
        this.transcript = transcript

        // AI 评分
        this.submitStep = 'scoring'
        const result = await evaluateAnswer({
          questionId: this.currentQuestion.id,
          transcript,
          examId: this.examId
        })
        this.scoringResult = result

        // 保存答案
        this.answers.push({
          questionId: this.currentQuestion.id,
          questionIndex: this.currentIndex,
          questionStem: this.currentQuestion.stem || '',
          dimension: this.currentQuestion.dimension || '',
          prepTime: this.currentQuestion.prepTime,
          answerTime: this.currentQuestion.answerTime,
          recordingBlob: blob || null,
          mediaUrl: uploadResult?.fileUrl || '',
          mediaType: uploadResult?.mediaType || options.mediaMimeType || blob?.type || '',
          mediaFilename: uploadResult?.originalFilename || options.mediaFileName || '',
          mediaSource: uploadResult?.source || options.mediaSource || (blob ? 'live_recording' : 'text'),
          transcript,
          scoringResult: result,
          submittedAt: new Date().toISOString()
        })

        this.status = EXAM_STATUS.COMPLETED
        this.submitStep = ''
        this.persistSession()
      } catch (err) {
        this.status = EXAM_STATUS.ANSWERING
        this.submitStep = ''
        this.persistSession()
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
      this.persistSession()
    },

    exitExam() {
      this.clearPersistedSession()
    },

    setDeviceReady(ready) {
      this.deviceReady = ready
      this.persistSession()
    },

    setVideoEnabled(enabled) {
      this.videoEnabled = enabled
      this.persistSession()
    },

    syncExamElapsed(elapsed) {
      const nextElapsed = Number(elapsed)
      this.examElapsed = Number.isFinite(nextElapsed) && nextElapsed >= 0 ? Math.round(nextElapsed) : 0
      this.persistSession()
    }
  }
})
