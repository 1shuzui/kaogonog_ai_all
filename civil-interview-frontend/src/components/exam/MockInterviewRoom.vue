<template>
  <div v-if="examStore.currentQuestion" class="mock-room">
    <div class="mock-room__bg" :style="{ backgroundImage: `url(${mockRoomBg})` }"></div>
    <div class="mock-room__overlay"></div>

    <div v-if="!isOnline" class="mock-room__offline-banner">
      当前网络异常，录音提交可能受影响，请尽量保持网络稳定。
    </div>

    <header class="mock-room__topbar">
      <div class="mock-room__topbar-left">
        <span class="mock-room__badge">AI 模拟考场</span>
        <span class="mock-room__meta">{{ candidateLabel }}</span>
      </div>
      <div class="mock-room__topbar-right">
        <div class="mock-room__timer">
          <FieldTimeOutlined />
          <div>
            <span class="mock-room__timer-label">总倒计时</span>
            <strong>{{ formattedTotalRemaining }}</strong>
          </div>
        </div>
        <a-popconfirm
          title="确定退出本场模拟面试吗？已完成的答题记录会先尝试保存。"
          @confirm="exitExam"
        >
          <a-button type="text" class="mock-room__exit">
            <CloseOutlined /> 退出
          </a-button>
        </a-popconfirm>
      </div>
    </header>

    <section class="mock-room__judges card-shell">
      <div class="mock-room__section-head">
        <div>
          <span class="section-kicker">考官席</span>
          <h2>模拟公务员面试现场</h2>
        </div>
        <a-button type="text" class="mock-room__replay" @click="playOpeningSpeech(true)">
          <SoundOutlined /> 重播引导语
        </a-button>
      </div>

      <div class="judge-speech">
        <div class="judge-speech__avatar">AI</div>
        <div class="judge-speech__content">
          <span class="judge-speech__title">主考官发言</span>
          <p>{{ examinerNotice }}</p>
          <div class="judge-speech__actions">
            <a-button
              v-if="!mockStarted"
              type="primary"
              size="large"
              @click="beginMockExam"
            >
              <PlayCircleOutlined /> 我已准备好，开始作答
            </a-button>
            <span v-else-if="speechInProgress" class="judge-speech__hint">
              正在播报考场引导语...
            </span>
            <span v-else class="judge-speech__hint">
              可滑动查看全部题目，但需按顺序完成作答。
            </span>
          </div>
        </div>
      </div>

      <div class="judge-grid">
        <div
          v-for="judge in judges"
          :key="judge.role"
          class="judge-card"
          :class="{ 'judge-card--lead': judge.lead }"
        >
          <div class="judge-card__avatar">{{ judge.short }}</div>
          <div class="judge-card__meta">
            <strong>{{ judge.role }}</strong>
            <span>{{ judge.label }}</span>
          </div>
        </div>
      </div>
    </section>

    <section class="mock-room__workspace">
      <section class="mock-room__questions card-shell">
      <div class="mock-room__section-head mock-room__section-head--compact">
        <div>
          <span class="section-kicker">题本区</span>
          <h3>共 {{ examStore.totalQuestions }} 题，总时长 {{ totalDurationMinutes }} 分钟</h3>
        </div>
        <div class="question-progress">
          <span>已完成 {{ examStore.answers.length }}/{{ examStore.totalQuestions }}</span>
          <strong v-if="allAnswered">全部作答完成</strong>
          <strong v-else>当前应作答第 {{ nextPendingIndex + 1 }} 题</strong>
        </div>
      </div>

      <div ref="questionStripRef" class="question-strip">
        <article
          v-for="(question, index) in examStore.questionList"
          :key="question.id || index"
          :data-question-index="index"
          class="question-card"
          :class="questionCardClass(index)"
          @click="selectQuestion(index)"
        >
          <div class="question-card__top">
            <span class="question-card__index">第 {{ index + 1 }} 题</span>
            <span class="question-card__status">{{ questionStatusText(index) }}</span>
          </div>
          <div class="question-card__stem">{{ question.stem }}</div>
          <div class="question-card__meta">
            <span>{{ getDimensionLabel(question.dimension) }}</span>
            <span>建议 {{ formatQuestionMinutes(question) }} 分钟</span>
          </div>
        </article>
      </div>

      <div class="question-nav">
        <a-button @click="goPrevQuestion" :disabled="!canGoPrev">
          <CaretLeftOutlined /> 上一题
        </a-button>
        <a-button @click="goNextQuestion" :disabled="!canGoNext">
          下一题 <CaretRightOutlined />
        </a-button>
      </div>
      </section>

      <section class="mock-room__candidate">
        <div class="candidate-stack">
          <div class="candidate-seat card-shell">
        <div class="candidate-seat__head">
          <div>
            <span class="section-kicker">考生席</span>
            <h3>{{ candidateLabel }}</h3>
          </div>
          <div class="candidate-seat__status" :class="{ 'is-recording': isAnsweringActiveQuestion }">
            {{ candidateStatusText }}
          </div>
        </div>

        <div class="candidate-seat__video">
          <VideoPreview
            :stream="stream"
            :recording="isAnsweringActiveQuestion"
            :duration="recorderDuration"
          />
        </div>

        <div v-show="isAnsweringActiveQuestion" class="candidate-seat__wave">
          <AudioWaveform
            :stream="stream"
            :active="isAnsweringActiveQuestion"
            :width="320"
            :height="56"
          />
        </div>
          </div>

          <div class="candidate-panel card-shell">
        <div class="candidate-panel__head">
          <div>
            <span class="section-kicker">作答控制</span>
            <h3>{{ currentQuestionTitle }}</h3>
          </div>
          <a-tag :color="currentQuestionTag.color">{{ currentQuestionTag.text }}</a-tag>
        </div>

        <p class="candidate-panel__hint">{{ currentQuestionHint }}</p>

        <div v-if="currentAnswer && isAnsweredQuestion(examStore.currentIndex)" class="candidate-panel__summary">
          本题已提交，可继续查看题干，或前往下一题继续作答。
        </div>

        <div class="candidate-panel__actions">
          <a-button
            v-if="!mockStarted"
            type="primary"
            size="large"
            block
            @click="beginMockExam"
          >
            <PlayCircleOutlined /> 开始本场面试
          </a-button>

          <template v-else-if="allAnswered">
            <a-button type="primary" size="large" block @click="finishExam">
              <CheckOutlined /> 结束面试并查看结果
            </a-button>
          </template>

          <template v-else-if="isFutureQuestion(examStore.currentIndex)">
            <a-button size="large" block disabled>
              <LockOutlined /> 请先完成第 {{ nextPendingIndex + 1 }} 题
            </a-button>
            <a-button size="large" block @click="returnToPendingQuestion">
              返回当前应作答题
            </a-button>
          </template>

          <template v-else-if="isViewingPastAnsweredQuestion">
            <a-button type="primary" size="large" block @click="returnToPendingQuestion">
              <PlayCircleOutlined /> 返回第 {{ nextPendingIndex + 1 }} 题继续作答
            </a-button>
          </template>

          <template v-else-if="examStore.status === EXAM_STATUS.IDLE">
            <a-button type="primary" size="large" block @click="startCurrentAnswer">
              <AudioOutlined /> 开始回答本题
            </a-button>
          </template>

          <template v-else-if="examStore.status === EXAM_STATUS.ANSWERING">
            <a-button danger type="primary" size="large" block @click="submitCurrentAnswer()">
              <CheckCircleFilled /> 提交本题答案
            </a-button>
          </template>

          <template v-else-if="examStore.status === EXAM_STATUS.SUBMITTING">
            <a-button size="large" block loading disabled>
              正在提交并评分...
            </a-button>
          </template>

          <template v-else-if="examStore.status === EXAM_STATUS.COMPLETED">
            <a-button
              v-if="!examStore.isLastQuestion"
              type="primary"
              size="large"
              block
              @click="goNextQuestion"
            >
              <CaretRightOutlined /> 进入下一题
            </a-button>
            <a-button v-else type="primary" size="large" block @click="finishExam">
              <CheckOutlined /> 全部完成，查看结果
            </a-button>
          </template>
        </div>
          </div>
        </div>
      </section>
    </section>
  </div>

  <div v-else class="mock-room mock-room--empty">
    <p>暂无题目，请返回重新开始。</p>
    <a-button type="primary" @click="$router.push('/')">返回首页</a-button>
  </div>
</template>

<script setup>
import { computed, nextTick, onMounted, onUnmounted, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { message } from 'ant-design-vue'
import {
  AudioOutlined,
  CaretLeftOutlined,
  CaretRightOutlined,
  CheckCircleFilled,
  CheckOutlined,
  CloseOutlined,
  FieldTimeOutlined,
  LockOutlined,
  PlayCircleOutlined,
  SoundOutlined
} from '@ant-design/icons-vue'
import { completeExam } from '@/api/exam'
import { useNetworkStatus } from '@/composables/useNetworkStatus'
import { useMediaRecorder } from '@/composables/useMediaRecorder'
import { useExamStore } from '@/stores/exam'
import { DIMENSIONS, EXAM_STATUS } from '@/utils/constants'
import AudioWaveform from '@/components/recording/AudioWaveform.vue'
import VideoPreview from '@/components/recording/VideoPreview.vue'
import mockRoomBg from '@/assets/exam/mock-interview-ai-clean.jpg'

const router = useRouter()
const route = useRoute()
const examStore = useExamStore()
const recorder = useMediaRecorder()
const { isOnline } = useNetworkStatus()

const stream = recorder.stream
const recorderDuration = recorder.duration
const questionStripRef = ref(null)

const mockStarted = ref(false)
const speechInProgress = ref(false)
const totalRemainingSeconds = ref(0)
const finishRequested = ref(false)

let totalTimer = null
let speechUtterance = null

const judges = [
  { role: '主考官', label: '综合统筹', short: '主', lead: true },
  { role: 'AI考官一', label: '政策理解', short: '策' },
  { role: 'AI考官二', label: '逻辑结构', short: '逻' },
  { role: 'AI考官三', label: '表达感染力', short: '达' },
  { role: 'AI考官四', label: '应变能力', short: '变' },
  { role: 'AI考官五', label: '岗位匹配', short: '岗' },
  { role: '计时席', label: '全场计时', short: '时' }
]

const candidateLabel = computed(() => {
  const raw = String(route.query.candidateNo || '01').trim()
  const normalized = /^\d+$/.test(raw) ? raw.padStart(2, '0') : raw
  return `${normalized}号考生`
})

const totalDurationSeconds = computed(() => examStore.questionList.reduce((sum, question) => {
  const prep = Math.max(0, Number(question?.prepTime) || 90)
  const answer = Math.max(0, Number(question?.answerTime) || 180)
  return sum + prep + answer
}, 0))

const totalDurationMinutes = computed(() => Math.max(1, Math.ceil(totalDurationSeconds.value / 60)))
const formattedTotalRemaining = computed(() => formatClock(totalRemainingSeconds.value))
const nextPendingIndex = computed(() => Math.min(examStore.answers.length, Math.max(examStore.totalQuestions - 1, 0)))
const allAnswered = computed(() => examStore.answers.length >= examStore.totalQuestions && examStore.totalQuestions > 0)
const currentAnswer = computed(() => examStore.currentAnswer)
const isViewingPastAnsweredQuestion = computed(() => {
  if (!currentAnswer.value) return false
  return examStore.currentIndex < examStore.answers.length
})
const isAnsweringActiveQuestion = computed(() => (
  mockStarted.value
  && examStore.status === EXAM_STATUS.ANSWERING
  && examStore.currentIndex === examStore.answers.length
))

const openingSpeechText = computed(() => (
  `${candidateLabel.value}，请就座。欢迎参加今天的面试，希望通过交流增进对你的了解。`
  + `本次面试共有 ${examStore.totalQuestions} 道题目，时间为 ${totalDurationMinutes.value} 分钟。请开始作答。`
))

const examinerNotice = computed(() => {
  if (!mockStarted.value) return openingSpeechText.value
  if (allAnswered.value) return '本场题目已全部作答完成，请点击下方按钮结束面试并查看结果。'
  if (totalRemainingSeconds.value <= 60) return '距离本场面试结束不足 1 分钟，请注意统筹剩余时间。'
  if (isFutureQuestion(examStore.currentIndex)) {
    return `当前题目可提前浏览，但请先完成第 ${nextPendingIndex.value + 1} 题。`
  }
  if (currentAnswer.value) {
    return `第 ${examStore.currentIndex + 1} 题已完成，可返回查看，也可继续后续题目。`
  }
  if (examStore.status === EXAM_STATUS.ANSWERING) {
    return `请继续回答第 ${examStore.currentIndex + 1} 题，注意把控整体答题节奏。`
  }
  return `现在开始回答第 ${examStore.currentIndex + 1} 题。`
})

const candidateStatusText = computed(() => {
  if (!mockStarted.value) return '等待开场'
  if (examStore.status === EXAM_STATUS.ANSWERING) return '正在录制作答'
  if (examStore.status === EXAM_STATUS.SUBMITTING) return '答案提交中'
  if (allAnswered.value) return '作答完成'
  return '待作答'
})

const currentQuestionTitle = computed(() => {
  if (!examStore.currentQuestion) return '当前题目'
  return `第 ${examStore.currentIndex + 1} 题`
})

const currentQuestionTag = computed(() => {
  if (allAnswered.value) return { text: '已完成', color: 'success' }
  if (isFutureQuestion(examStore.currentIndex)) return { text: '预览中', color: 'blue' }
  if (currentAnswer.value) return { text: '已提交', color: 'success' }
  if (!mockStarted.value) return { text: '待开始', color: 'blue' }
  if (examStore.status === EXAM_STATUS.ANSWERING) return { text: '作答中', color: 'processing' }
  if (examStore.status === EXAM_STATUS.SUBMITTING) return { text: '评分中', color: 'warning' }
  return { text: '待作答', color: 'gold' }
})

const currentQuestionHint = computed(() => {
  if (!mockStarted.value) return '开场引导语播放完成后，点击开始作答即可进入真实考场节奏。'
  if (allAnswered.value) return '所有题目均已提交，可以结束本场模拟面试。'
  if (isFutureQuestion(examStore.currentIndex)) {
    return `你可以先浏览这道题，但系统只允许按顺序从第 ${nextPendingIndex.value + 1} 题开始作答。`
  }
  if (isViewingPastAnsweredQuestion.value) {
    return '这是一道已完成题目，可回看题干内容，不能重复提交。'
  }
  if (examStore.status === EXAM_STATUS.ANSWERING) {
    return '当前正在录制，请保持正常答题节奏，答完后手动提交本题。'
  }
  if (examStore.status === EXAM_STATUS.SUBMITTING) {
    return '系统正在上传录音并进行评分，请稍候。'
  }
  return '请点击“开始回答本题”，系统会录制你的作答内容并在提交后进入下一步。'
})

const canGoPrev = computed(() => examStore.currentIndex > 0 && examStore.status !== EXAM_STATUS.SUBMITTING && examStore.status !== EXAM_STATUS.ANSWERING)
const canGoNext = computed(() => examStore.currentIndex < examStore.totalQuestions - 1 && examStore.status !== EXAM_STATUS.SUBMITTING && examStore.status !== EXAM_STATUS.ANSWERING)

onMounted(async () => {
  await new Promise((resolve) => setTimeout(resolve, 300))
  const currentStream = await recorder.initStream({ videoEnabled: examStore.videoEnabled })
  if (!currentStream) {
    await new Promise((resolve) => setTimeout(resolve, 500))
    await recorder.initStream({ videoEnabled: examStore.videoEnabled })
  }

  examStore.goToQuestion(0)
  totalRemainingSeconds.value = totalDurationSeconds.value

  await nextTick()
  scrollCurrentQuestionIntoView()
  playOpeningSpeech()
})

onUnmounted(() => {
  stopTotalTimer()
  stopSpeech()
  recorder.destroyStream()
})

watch(() => examStore.currentIndex, async () => {
  await nextTick()
  scrollCurrentQuestionIntoView()
})

function formatClock(totalSeconds = 0) {
  const safe = Math.max(0, Number(totalSeconds) || 0)
  const minutes = Math.floor(safe / 60)
  const seconds = safe % 60
  return `${String(minutes).padStart(2, '0')}:${String(seconds).padStart(2, '0')}`
}

function getDimensionLabel(key) {
  const matched = DIMENSIONS.find((item) => item.key === key)
  return matched ? matched.name : key || '综合题'
}

function formatQuestionMinutes(question) {
  const seconds = Math.max(60, Number(question?.prepTime || 90) + Number(question?.answerTime || 180))
  return Math.max(1, Math.ceil(seconds / 60))
}

function isAnsweredQuestion(index) {
  return examStore.answers.some((item) => item.questionIndex === index)
}

function isFutureQuestion(index) {
  return index > examStore.answers.length
}

function questionStatusText(index) {
  if (isAnsweredQuestion(index)) return '已作答'
  if (index === examStore.answers.length) return mockStarted.value ? '当前作答位' : '待开始'
  return '可预览'
}

function questionCardClass(index) {
  return {
    'is-current': index === examStore.currentIndex,
    'is-answered': isAnsweredQuestion(index),
    'is-pending': index === examStore.answers.length && !isAnsweredQuestion(index),
    'is-future': isFutureQuestion(index)
  }
}

function selectQuestion(index) {
  if (examStore.status === EXAM_STATUS.ANSWERING) {
    message.warning('请先提交当前正在录制的答案。')
    return
  }
  if (examStore.status === EXAM_STATUS.SUBMITTING) {
    message.warning('本题仍在提交中，请稍候。')
    return
  }
  examStore.goToQuestion(index)
}

function goPrevQuestion() {
  if (!canGoPrev.value) return
  examStore.previousQuestion()
}

function goNextQuestion() {
  if (!canGoNext.value) return
  examStore.nextQuestion()
}

function returnToPendingQuestion() {
  if (allAnswered.value) {
    examStore.goToQuestion(examStore.totalQuestions - 1)
    return
  }
  examStore.goToQuestion(examStore.answers.length)
}

function scrollCurrentQuestionIntoView() {
  const container = questionStripRef.value
  if (!container) return
  const current = container.querySelector(`[data-question-index="${examStore.currentIndex}"]`)
  current?.scrollIntoView({ behavior: 'smooth', inline: 'center', block: 'nearest' })
}

function stopSpeech() {
  if (typeof window === 'undefined' || !window.speechSynthesis) return
  window.speechSynthesis.cancel()
  speechUtterance = null
  speechInProgress.value = false
}

function playOpeningSpeech(forceReplay = false) {
  if (typeof window === 'undefined' || !window.speechSynthesis) return
  if (mockStarted.value && !forceReplay) return

  stopSpeech()

  const utterance = new window.SpeechSynthesisUtterance(openingSpeechText.value)
  utterance.lang = 'zh-CN'
  utterance.rate = 0.94
  utterance.pitch = 1
  utterance.onstart = () => {
    speechInProgress.value = true
  }
  utterance.onend = () => {
    speechInProgress.value = false
  }
  utterance.onerror = () => {
    speechInProgress.value = false
  }

  speechUtterance = utterance
  window.speechSynthesis.speak(utterance)
}

function beginMockExam() {
  if (mockStarted.value) return
  stopSpeech()
  mockStarted.value = true
  examStore.examStartTime = Date.now()
  examStore.goToQuestion(0)
  totalRemainingSeconds.value = totalDurationSeconds.value
  startTotalTimer()
}

function startTotalTimer() {
  stopTotalTimer()
  totalTimer = setInterval(() => {
    const elapsed = Math.floor((Date.now() - examStore.examStartTime) / 1000)
    totalRemainingSeconds.value = Math.max(0, totalDurationSeconds.value - elapsed)
    if (totalRemainingSeconds.value <= 0) {
      stopTotalTimer()
      handleTimeUp()
    }
  }, 250)
}

function stopTotalTimer() {
  clearInterval(totalTimer)
  totalTimer = null
}

async function startCurrentAnswer() {
  if (!mockStarted.value) {
    beginMockExam()
    return
  }
  if (isFutureQuestion(examStore.currentIndex)) {
    message.warning(`请先完成第 ${nextPendingIndex.value + 1} 题。`)
    return
  }
  if (currentAnswer.value) {
    message.info('这道题已经提交过了，请前往下一题。')
    return
  }

  stopSpeech()
  examStore.resetCurrentQuestionState()
  const started = recorder.startRecording()
  if (!started) {
    message.error(recorder.error.value || '录制启动失败，请检查设备权限后重试')
    return
  }
  examStore.startAnswering()
}

async function submitCurrentAnswer(options = {}) {
  const { finishAfterSubmit = false } = options

  if (examStore.status !== EXAM_STATUS.ANSWERING) return

  try {
    const blob = await recorder.stopRecording()
    await examStore.submitAnswer(blob)

    if (finishAfterSubmit || totalRemainingSeconds.value <= 0) {
      await finishExam()
    }
  } catch (error) {
    if (!error?.normalizedMessage) {
      message.error(`提交失败：${error?.message || '未知错误'}`)
    }
  }
}

async function handleTimeUp() {
  message.warning('总计时结束，系统将结束本场模拟面试。')

  if (examStore.status === EXAM_STATUS.ANSWERING) {
    await submitCurrentAnswer({ finishAfterSubmit: true })
    return
  }

  await finishExam()
}

async function finishExam() {
  if (finishRequested.value) return
  finishRequested.value = true

  stopTotalTimer()
  stopSpeech()

  const examId = examStore.examId
  if (!examId) {
    message.error('考试数据异常，请返回首页重新开始。')
    finishRequested.value = false
    router.push('/')
    return
  }

  try {
    await completeExam(examId)
  } catch (error) {
    console.error('保存面试记录失败:', error)
  }

  recorder.destroyStream()
  router.push(`/result/${examId}`)
}

async function exitExam() {
  stopTotalTimer()
  stopSpeech()

  if (examStore.status === EXAM_STATUS.ANSWERING) {
    try {
      await recorder.stopRecording()
    } catch {}
  }

  if (examStore.examId && examStore.answers.length > 0) {
    try {
      await completeExam(examStore.examId)
      message.success('已保存当前面试进度。')
    } catch (error) {
      console.error('保存面试记录失败:', error)
    }
  }

  recorder.destroyStream()
  examStore.exitExam()
  router.push('/')
}
</script>

<style lang="less" scoped>
@import '@/styles/variables.less';

.mock-room {
  position: relative;
  min-height: 100vh;
  padding: 14px 16px 18px;
  color: #fff;
  overflow: hidden;
  background: #1d1e23;
}

.mock-room__bg,
.mock-room__overlay {
  position: fixed;
  inset: 0;
  pointer-events: none;
}

.mock-room__bg {
  background-position: center 14%;
  background-size: cover;
  filter: saturate(0.96) contrast(1.04) brightness(0.58);
  transform: scale(1.03);
}

.mock-room__overlay {
  background:
    linear-gradient(180deg, rgba(15, 17, 23, 0.14) 0%, rgba(15, 17, 23, 0.46) 42%, rgba(15, 17, 23, 0.84) 68%, rgba(15, 17, 23, 0.95) 100%),
    radial-gradient(circle at top center, rgba(255, 240, 209, 0.16), transparent 38%),
    linear-gradient(135deg, rgba(138, 22, 22, 0.12), transparent 24%);
}

.mock-room > * {
  position: relative;
  z-index: 1;
}

.mock-room__offline-banner {
  margin-bottom: 12px;
  padding: 10px 14px;
  border-radius: 14px;
  background: rgba(255, 241, 240, 0.92);
  color: #cf1322;
  font-size: @font-size-sm;
  font-weight: 600;
}

.mock-room__topbar {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 16px;
  margin-bottom: 14px;
}

.mock-room__topbar-left,
.mock-room__topbar-right {
  display: flex;
  align-items: center;
  gap: 10px;
}

.mock-room__badge,
.mock-room__meta {
  display: inline-flex;
  align-items: center;
  min-height: 38px;
  padding: 0 14px;
  border-radius: 999px;
  background: rgba(255, 255, 255, 0.12);
  backdrop-filter: blur(12px);
  font-size: @font-size-sm;
}

.mock-room__badge {
  font-weight: 700;
  letter-spacing: 0.4px;
}

.mock-room__timer {
  display: inline-flex;
  align-items: center;
  gap: 10px;
  min-height: 44px;
  padding: 0 14px;
  border-radius: 18px;
  background: rgba(15, 17, 23, 0.72);
  border: 1px solid rgba(255, 255, 255, 0.1);
  backdrop-filter: blur(14px);

  .anticon {
    font-size: 18px;
    color: #ffd77a;
  }

  strong {
    display: block;
    color: #fff;
    font-size: 18px;
    line-height: 1.1;
    font-variant-numeric: tabular-nums;
  }
}

.mock-room__timer-label {
  display: block;
  color: rgba(255, 255, 255, 0.72);
  font-size: 11px;
}

.mock-room__exit {
  color: rgba(255, 255, 255, 0.82);
}

.card-shell {
  border-radius: 28px;
  border: 1px solid rgba(255, 255, 255, 0.1);
  background: rgba(18, 20, 27, 0.56);
  box-shadow: 0 20px 48px rgba(7, 9, 14, 0.26);
  backdrop-filter: blur(18px);
}

.mock-room__judges {
  display: flex;
  flex-direction: column;
  justify-content: space-between;
  min-height: 42vh;
  padding: 18px 22px 22px;
  background:
    linear-gradient(180deg, rgba(15, 17, 23, 0.1) 0%, rgba(15, 17, 23, 0.3) 40%, rgba(15, 17, 23, 0.7) 100%),
    rgba(18, 20, 27, 0.18);
  border-color: rgba(255, 255, 255, 0.08);
}

.mock-room__workspace {
  display: grid;
  grid-template-columns: minmax(0, 1.25fr) minmax(320px, 0.92fr);
  gap: 14px;
  align-items: start;
}

.mock-room__questions {
  padding: 18px;
  background: rgba(15, 17, 23, 0.72);
}

.mock-room__candidate {
  min-width: 0;
}

.candidate-stack {
  display: grid;
  gap: 14px;
}

.candidate-seat,
.candidate-panel {
  padding: 18px;
}

.candidate-seat {
  background:
    linear-gradient(180deg, rgba(255, 255, 255, 0.08) 0%, rgba(17, 19, 24, 0.88) 100%);
}

.candidate-panel {
  background:
    linear-gradient(180deg, rgba(153, 29, 29, 0.16) 0%, rgba(17, 19, 24, 0.9) 100%);
}

.mock-room__section-head {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  gap: 12px;
  margin-bottom: 16px;

  h2,
  h3 {
    margin: 4px 0 0;
    color: #fff;
  }

  h2 {
    font-size: 30px;
    line-height: 1.12;
  }

  h3 {
    font-size: 22px;
    line-height: 1.2;
  }
}

.mock-room__section-head--compact {
  align-items: center;
}

.section-kicker {
  display: inline-flex;
  align-items: center;
  padding: 4px 10px;
  border-radius: 999px;
  background: rgba(255, 255, 255, 0.12);
  color: rgba(255, 255, 255, 0.82);
  font-size: 12px;
  letter-spacing: 1px;
}

.mock-room__replay {
  color: rgba(255, 255, 255, 0.8);
}

.judge-speech {
  display: grid;
  grid-template-columns: 72px minmax(0, 1fr);
  gap: 16px;
  max-width: 760px;
  padding: 18px 20px;
  border-radius: 22px;
  background: linear-gradient(135deg, rgba(157, 26, 26, 0.82) 0%, rgba(72, 10, 10, 0.76) 100%);
  box-shadow: inset 0 1px 0 rgba(255, 255, 255, 0.1);
}

.judge-speech__avatar,
.judge-card__avatar {
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: 50%;
  font-weight: 700;
}

.judge-speech__avatar {
  width: 72px;
  height: 72px;
  background: radial-gradient(circle at 30% 30%, #fff0cb 0%, #f7c66a 32%, #9d2626 100%);
  color: #5b0707;
  font-size: 22px;
}

.judge-speech__content {
  min-width: 0;
}

.judge-speech__title {
  display: block;
  color: rgba(255, 255, 255, 0.74);
  font-size: 12px;
  letter-spacing: 1px;
  margin-bottom: 8px;
}

.judge-speech__content p {
  margin: 0;
  color: #fffaf2;
  font-size: 20px;
  line-height: 1.8;
}

.judge-speech__actions {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-top: 14px;
}

.judge-speech__hint {
  color: rgba(255, 255, 255, 0.76);
  font-size: @font-size-sm;
}

.judge-grid {
  display: grid;
  grid-template-columns: repeat(7, minmax(0, 1fr));
  gap: 10px;
  max-width: 760px;
  margin-top: 18px;
  margin-left: auto;
}

.judge-card {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 10px;
  padding: 14px 10px;
  border-radius: 20px;
  background: rgba(255, 255, 255, 0.09);
  border: 1px solid rgba(255, 255, 255, 0.1);
  backdrop-filter: blur(10px);
  text-align: center;
}

.judge-card--lead {
  background: linear-gradient(180deg, rgba(255, 215, 122, 0.16) 0%, rgba(255, 255, 255, 0.08) 100%);
  border-color: rgba(255, 215, 122, 0.26);
}

.judge-card__avatar {
  width: 52px;
  height: 52px;
  background: linear-gradient(135deg, rgba(255, 255, 255, 0.9) 0%, rgba(255, 215, 122, 0.88) 100%);
  color: #6b0d0d;
  font-size: 18px;
}

.judge-card__meta {
  display: flex;
  flex-direction: column;
  gap: 4px;

  strong {
    color: #fff;
    font-size: @font-size-base;
  }

  span {
    color: rgba(255, 255, 255, 0.62);
    font-size: 12px;
  }
}

.question-progress {
  display: flex;
  flex-direction: column;
  align-items: flex-end;
  gap: 4px;
  color: rgba(255, 255, 255, 0.75);
  font-size: @font-size-sm;

  strong {
    color: #fff;
  }
}

.question-strip {
  display: grid;
  grid-auto-flow: column;
  grid-auto-columns: minmax(300px, 38vw);
  gap: 12px;
  overflow-x: auto;
  padding-bottom: 8px;
  scroll-snap-type: x mandatory;
}

.question-strip::-webkit-scrollbar {
  height: 8px;
}

.question-strip::-webkit-scrollbar-thumb {
  border-radius: 999px;
  background: rgba(255, 255, 255, 0.18);
}

.question-card {
  scroll-snap-align: start;
  min-height: 224px;
  padding: 18px;
  border-radius: 22px;
  border: 1px solid rgba(255, 255, 255, 0.1);
  background: rgba(255, 255, 255, 0.07);
  cursor: pointer;
  transition: transform 0.22s ease, border-color 0.22s ease, box-shadow 0.22s ease;
}

.question-card:hover {
  transform: translateY(-2px);
}

.question-card.is-current {
  border-color: rgba(255, 215, 122, 0.6);
  box-shadow: 0 14px 26px rgba(0, 0, 0, 0.18);
}

.question-card.is-answered {
  background: rgba(23, 78, 49, 0.36);
  border-color: rgba(96, 201, 140, 0.22);
}

.question-card.is-pending {
  background: rgba(177, 90, 17, 0.18);
  border-color: rgba(255, 215, 122, 0.24);
}

.question-card.is-future {
  background: rgba(255, 255, 255, 0.06);
}

.question-card__top,
.question-card__meta {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 10px;
}

.question-card__index,
.question-card__status,
.question-card__meta {
  font-size: @font-size-xs;
  color: rgba(255, 255, 255, 0.72);
}

.question-card__status {
  padding: 4px 8px;
  border-radius: 999px;
  background: rgba(255, 255, 255, 0.08);
}

.question-card__stem {
  margin: 16px 0 20px;
  font-size: 16px;
  line-height: 1.9;
  color: rgba(255, 255, 255, 0.96);
  word-break: break-word;
}

.question-nav {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 10px;
  margin-top: 14px;
}

.candidate-seat__head,
.candidate-panel__head {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  gap: 12px;
  margin-bottom: 14px;

  h3 {
    margin: 4px 0 0;
    color: #fff;
  }
}

.candidate-seat__status {
  padding: 6px 12px;
  border-radius: 999px;
  background: rgba(255, 255, 255, 0.1);
  color: rgba(255, 255, 255, 0.86);
  font-size: @font-size-xs;
}

.candidate-seat__status.is-recording {
  background: rgba(207, 19, 34, 0.2);
  color: #ffd5d5;
}

.candidate-seat__video {
  aspect-ratio: 16 / 10;
  border-radius: 24px;
  overflow: hidden;
  background: #000;
  border: 1px solid rgba(255, 255, 255, 0.1);
}

.candidate-seat__wave {
  margin-top: 14px;
  padding: 10px 14px;
  border-radius: 16px;
  background: rgba(255, 255, 255, 0.06);
}

.candidate-panel__hint {
  margin: 0 0 12px;
  color: rgba(255, 255, 255, 0.82);
  line-height: 1.8;
}

.candidate-panel__summary {
  padding: 12px 14px;
  border-radius: 16px;
  background: rgba(255, 255, 255, 0.08);
  color: rgba(255, 255, 255, 0.72);
  font-size: @font-size-sm;
  line-height: 1.7;
}

.candidate-panel__actions {
  display: flex;
  flex-direction: column;
  gap: 10px;
  margin-top: 18px;
}

.candidate-panel__actions :deep(.ant-btn-lg) {
  min-height: 48px;
}

.mock-room--empty {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 14px;
}

@media (max-width: 1200px) {
  .mock-room__workspace {
    grid-template-columns: 1fr;
  }

  .judge-grid {
    grid-template-columns: repeat(4, minmax(0, 1fr));
  }

  .question-strip {
    grid-auto-columns: minmax(280px, 46vw);
  }

  .candidate-stack {
    grid-template-columns: repeat(2, minmax(0, 1fr));
    align-items: start;
  }
}

@media (max-width: 900px) {
  .mock-room {
    padding: 12px;
  }

  .mock-room__topbar,
  .mock-room__topbar-right {
    flex-direction: column;
    align-items: stretch;
  }

  .judge-grid {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }

  .question-strip {
    grid-auto-columns: minmax(260px, 72vw);
  }

  .candidate-stack {
    grid-template-columns: 1fr;
  }
}

@media (max-width: 640px) {
  .mock-room__topbar-left,
  .mock-room__topbar-right,
  .mock-room__section-head,
  .candidate-seat__head,
  .candidate-panel__head {
    flex-direction: column;
    align-items: stretch;
  }

  .judge-speech {
    grid-template-columns: 1fr;
  }

  .judge-speech__avatar {
    margin: 0 auto;
  }

  .question-nav {
    justify-content: stretch;
    flex-direction: column;
  }

  .question-nav .ant-btn {
    width: 100%;
  }
}
</style>
