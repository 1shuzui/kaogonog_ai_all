/** Own elapsed/remaining time, shared Jiangsu deadlines and capture-pause accounting. */
import { ref, onScopeDispose } from 'vue'

export function useExamClock({ question, preferences, isJiangsuFullExamTiming }, runtime = {}) {
  const readNow = runtime.now || (() => Date.now())
  const scheduleInterval = runtime.setInterval || setInterval
  const cancelInterval = runtime.clearInterval || clearInterval
  // Explicit zero belongs to the question; it must not fall back to a saved preference.
  function questionSeconds(value, preferred, fallback) { return Number(value || preferred || fallback) }
  const phase = ref('preparing')
  const prepLeft = ref(preferences.value.defaultPrepTime)
  const answerLeft = ref(preferences.value.defaultAnswerTime)
  const overtimeSeconds = ref(0)
  const questionStartedAt = ref(readNow())
  let timer = null
  let timerPhase = ''
  let timerDeadline = 0
  let timerPausedAt = null
  const JIANGSU_READING_SECONDS = 5 * 60
  const JIANGSU_ANSWER_SECONDS = 15 * 60

  function startTimer() {
    cancelInterval(timer)
    timer = scheduleInterval(() => {
      if (timerPausedAt !== null) return
      const now = readNow()
      if (timerPhase !== phase.value) {
        timerPhase = phase.value
        timerDeadline = now + (phase.value === 'answering' ? answerLeft.value : prepLeft.value) * 1000
      }
      if (phase.value === 'preparing' || phase.value === 'reading') {
        prepLeft.value = Math.max(0, Math.ceil((timerDeadline - now) / 1000))
        if (prepLeft.value > 0) return
        phase.value = 'answering'
        timerPhase = 'answering'
        timerDeadline += answerLeft.value * 1000
      }
      answerLeft.value = Math.max(0, Math.ceil((timerDeadline - now) / 1000))
      overtimeSeconds.value = Math.max(0, Math.floor((now - timerDeadline) / 1000))
    }, 250)
  }

  function pauseCaptureClock() {
    if (timerPausedAt === null) timerPausedAt = readNow()
  }

  function resumeCaptureClock() {
    if (timerPausedAt === null) return
    const pausedMs = readNow() - timerPausedAt
    timerDeadline += pausedMs
    questionStartedAt.value += pausedMs
    timerPausedAt = null
  }

  function currentUsageSeconds() {
    const elapsed = Math.ceil(((timerPausedAt ?? readNow()) - questionStartedAt.value) / 1000)
    return Math.max(1, elapsed)
  }

  function standardQuestionSeconds() {
    if (isJiangsuFullExamTiming.value) {
      return JIANGSU_READING_SECONDS + JIANGSU_ANSWER_SECONDS
    }
    return questionSeconds(question.value?.prepTime, preferences.value.defaultPrepTime, 90)
      + questionSeconds(question.value?.answerTime, preferences.value.defaultAnswerTime, 180)
  }

  function buildTimingMeta() {
    const actualSeconds = currentUsageSeconds()
    const standardSeconds = Math.max(0, standardQuestionSeconds())
    return {
      actualSeconds,
      standardSeconds,
      overtimeSeconds: Math.max(0, actualSeconds - standardSeconds, Number(overtimeSeconds.value || 0))
    }
  }

  function resetQuestionClock() {
    phase.value = isJiangsuFullExamTiming.value ? 'reading' : 'preparing'
    prepLeft.value = isJiangsuFullExamTiming.value
      ? JIANGSU_READING_SECONDS
      : questionSeconds(question.value?.prepTime, preferences.value.defaultPrepTime, 90)
    answerLeft.value = isJiangsuFullExamTiming.value
      ? JIANGSU_ANSWER_SECONDS
      : questionSeconds(question.value?.answerTime, preferences.value.defaultAnswerTime, 180)
    overtimeSeconds.value = 0
    questionStartedAt.value = readNow()
    timerPhase = phase.value
    timerDeadline = questionStartedAt.value + prepLeft.value * 1000
  }

  function beginJiangsuAnswer() {
    phase.value = 'answering'
    prepLeft.value = 0
    answerLeft.value = Math.max(Number(answerLeft.value) || 0, JIANGSU_ANSWER_SECONDS)
    timerPhase = 'answering'
    timerDeadline = readNow() + answerLeft.value * 1000
    overtimeSeconds.value = 0
  }

  function stopTimer() { cancelInterval(timer); timer = null }
  onScopeDispose(stopTimer)
  return {
    phase,
    prepLeft,
    answerLeft,
    overtimeSeconds,
    questionStartedAt,
    startTimer,
    pauseCaptureClock,
    resumeCaptureClock,
    currentUsageSeconds,
    standardQuestionSeconds,
    buildTimingMeta,
    resetQuestionClock,
    beginJiangsuAnswer,
    stopTimer
  }
}
