<!--
全真模拟考场组件，按真实套题组织题目和时间，不强制先选考试大类再选地区。

@param: 通过 props、slot 和事件接收页面上下文；不直接拥有业务真源。
@return: 渲染可复用 UI，并通过 emit 或插槽把操作交还给父页面。
@raises: 不主动抛业务异常；异常状态应由父页面、请求层或兜底 UI 承接。
-->
<template>
  <div v-if="examStore.currentQuestion" class="full-exam-room learner-page">

    <div v-if="!isOnline" class="full-exam-room__offline-banner">
      当前网络异常，录音提交可能受影响，请尽量保持网络稳定。
    </div>

    <header class="full-exam-room__topbar">
      <div class="full-exam-room__topbar-left">
        <span class="full-exam-room__badge"><ReadOutlined /> 全真练习</span>
        <span class="full-exam-room__meta">{{ candidateLabel }}</span>
      </div>
      <div class="full-exam-room__topbar-right">
        <div class="full-exam-room__timer">
          <FieldTimeOutlined />
          <div>
            <span class="full-exam-room__timer-label">总倒计时</span>
            <strong>{{ formattedTotalRemaining }}</strong>
          </div>
        </div>
        <a-popconfirm
          title="确定退出本场全真模拟吗？已完成的答题记录会先尝试保存。"
          @confirm="exitExam"
        >
          <a-button type="text" class="full-exam-room__exit">
            <CloseOutlined /> 退出
          </a-button>
        </a-popconfirm>
      </div>
    </header>

    <section class="full-exam-room__judges card-shell">
      <div class="full-exam-room__section-head">
        <div>
          <span class="section-kicker">考场引导</span>
          <h2>{{ examStarted ? '专注眼前这一题。' : '调整呼吸，准备开始。' }}</h2>
        </div>
        <a-button type="text" class="full-exam-room__replay" @click="playOpeningSpeech(true)">
          <SoundOutlined /> 重播引导语
        </a-button>
      </div>

      <div class="judge-speech">
        <div class="judge-speech__avatar"><SoundOutlined /></div>
        <div class="judge-speech__content">
          <span class="judge-speech__title">主考官发言</span>
          <p>{{ examinerNotice }}</p>
          <div class="judge-speech__actions">
            <a-button
              v-if="!examStarted"
              type="primary"
              size="large"
              @click="beginExam"
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

      <details class="judge-stage">
        <summary>查看模拟考场</summary>
        <div class="judge-stage__scene">
          <canvas
            ref="judgeStageCanvasRef"
            class="judge-stage__image judge-stage__canvas"
            :width="judgeStageSceneSize.width"
            :height="judgeStageSceneSize.height"
            role="img"
            :aria-label="`${currentYearLabel}公务员面试现场`"
          ></canvas>
        </div>
      </details>
    </section>

    <section class="full-exam-room__workspace">
      <section class="full-exam-room__questions card-shell">
      <div class="full-exam-room__section-head full-exam-room__section-head--compact">
        <div>
          <span class="section-kicker">题本区</span>
          <h3>{{ timingSummary }}</h3>
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
          <QuestionMetaTags :question="question" emphasis compact basic-only />
          <div class="question-card__stem">
            <QuestionRichContent
              :text="question.stem"
              compact
              :collapsed-height="156"
            />
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

      <section class="full-exam-room__candidate">
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
          <div class="candidate-panel__head-side">
            <div class="candidate-panel__inline-timer">
              <FieldTimeOutlined />
              <span>{{ formattedTotalRemaining }}</span>
            </div>
            <a-tag :color="currentQuestionTag.color">{{ currentQuestionTag.text }}</a-tag>
          </div>
        </div>

        <div class="candidate-panel__question">
          <QuestionMetaTags :question="examStore.currentQuestion" emphasis basic-only />
          <div class="candidate-panel__question-body">
            <QuestionRichContent
              :text="examStore.currentQuestion?.stem || ''"
              scrollable
              :scroll-height="220"
              :collapsed-height="170"
            />
          </div>
        </div>

        <p class="candidate-panel__hint">{{ currentQuestionHint }}</p>

        <div v-if="finishRequested" class="candidate-panel__analysis">
          <a-spin size="small" />
          <span>{{ finalAnalysisText }}</span>
        </div>

        <div v-if="currentAnswer && isAnsweredQuestion(examStore.currentIndex)" class="candidate-panel__summary">
          本题已提交，可继续查看题干，或前往下一题继续作答。
        </div>

        <div class="candidate-panel__actions">
          <BackgroundAnswers />
          <a-button
            v-if="!examStarted"
            type="primary"
            size="large"
            block
            @click="beginExam"
          >
            <PlayCircleOutlined /> 开始本场全真模拟
          </a-button>

          <template v-else-if="allAnswered">
            <a-button
              type="primary"
              size="large"
              block
              :loading="finishRequested"
              :disabled="finishRequested"
              @click="finishExam"
            >
              <CheckOutlined /> {{ finishRequested ? '正在分析结果...' : '结束全真模拟并查看结果' }}
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
            <a-button type="primary" size="large" block :disabled="submittingAnswer" :loading="submittingAnswer" @click="submitCurrentAnswer()">
              <CheckCircleFilled /> {{ submittingAnswer ? '正在整理录音' : examStore.isLastQuestion ? '提交并结束作答' : '提交并继续' }}
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
            <a-button
              v-else
              type="primary"
              size="large"
              block
              :loading="finishRequested"
              :disabled="finishRequested"
              @click="finishExam"
            >
              <CheckOutlined /> {{ finishRequested ? '正在分析结果...' : '全部完成，查看结果' }}
            </a-button>
          </template>
        </div>
          </div>
        </div>
      </section>
    </section>
  </div>

  <div v-else class="full-exam-room full-exam-room--empty learner-page">
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
  ReadOutlined,
  SoundOutlined
} from '@ant-design/icons-vue'
import BackgroundAnswers from '@/components/exam/BackgroundAnswers.vue'
import { useNetworkStatus } from '@/composables/useNetworkStatus'
import { useMediaRecorder } from '@/composables/useMediaRecorder'
import { useExamStore } from '@/stores/exam'
import { EXAM_STATUS } from '@/utils/constants'
import AudioWaveform from '@/components/recording/AudioWaveform.vue'
import VideoPreview from '@/components/recording/VideoPreview.vue'
import QuestionMetaTags from '@/components/common/QuestionMetaTags.vue'
import QuestionRichContent from '@/components/common/QuestionRichContent.vue'
import { reportUsage } from '@/api/usage'
import { useBillingStore } from '@/stores/billing'
import { logger } from '@/utils/logger'
import fullExamRoomReference from '@/assets/exam/full-exam-room-live-current.jpg'

const router = useRouter()
const route = useRoute()
const examStore = useExamStore()
const billingStore = useBillingStore()
const recorder = useMediaRecorder()
const { isOnline } = useNetworkStatus()

const stream = recorder.stream
const recorderDuration = recorder.duration
const questionStripRef = ref(null)
const judgeStageCanvasRef = ref(null)
const judgeStageSceneSize = { width: 720, height: 404 }

const examStarted = ref(false)
const readingPhaseActive = ref(false)
const speechInProgress = ref(false)
const totalRemainingSeconds = ref(0)
const finishRequested = ref(false)
const submittingAnswer = ref(false)
const exitingExam = ref(false)
const currentYearLabel = `${new Date().getFullYear()}年度`
let totalTimer = null
let speechUtterance = null
const judgeStageSourceImageCache = new Map()
const judgeStageSourceImagePromiseCache = new Map()
const judgeTimerPanelConfig = {
  sourceX: 1519,
  sourceY: 374,
  sourceWidth: 124,
  sourceHeight: 58
}
const JIANGSU_FULL_EXAM_TIMING_MODE = 'jiangsu_5_15'
const JIANGSU_READING_SECONDS = 5 * 60
const JIANGSU_ANSWER_SECONDS = 15 * 60

function loadJudgeStageSourceImage() {
  const src = fullExamRoomReference
  const cached = judgeStageSourceImageCache.get(src)
  if (cached) return Promise.resolve(cached)

  const pending = judgeStageSourceImagePromiseCache.get(src)
  if (pending) return pending

  const promise = new Promise((resolve, reject) => {
    const image = new Image()
    image.onload = () => {
      judgeStageSourceImageCache.set(src, image)
      judgeStageSourceImagePromiseCache.delete(src)
      resolve(image)
    }
    image.onerror = (error) => {
      judgeStageSourceImagePromiseCache.delete(src)
      reject(error)
    }
    image.src = src
  })

  judgeStageSourceImagePromiseCache.set(src, promise)
  return promise
}

function mapSourceRectToCanvas(image, sourceRect) {
  const scaleX = judgeStageSceneSize.width / image.width
  const scaleY = judgeStageSceneSize.height / image.height
  return {
    x: sourceRect.sourceX * scaleX,
    y: sourceRect.sourceY * scaleY,
    width: sourceRect.sourceWidth * scaleX,
    height: sourceRect.sourceHeight * scaleY
  }
}

function drawTimerCutout(ctx, image) {
  const rect = mapSourceRectToCanvas(image, judgeTimerPanelConfig)
  const timeText = formattedTotalRemaining.value
  const maxTextWidth = rect.width * 0.9
  let fontSize = Math.max(16, rect.height * 0.66)

  ctx.save()
  ctx.fillStyle = '#191111'
  ctx.fillRect(rect.x, rect.y, rect.width, rect.height)
  ctx.fillStyle = 'rgba(70, 0, 0, 0.72)'
  ctx.fillRect(rect.x, rect.y, rect.width, rect.height * 0.1)
  ctx.fillStyle = '#ff2a2a'
  ctx.shadowColor = 'rgba(255, 16, 16, 0.9)'
  ctx.shadowBlur = Math.max(4, rect.height * 0.08)
  ctx.textAlign = 'center'
  ctx.textBaseline = 'middle'
  ctx.font = `800 ${fontSize}px "Arial", "DIN Alternate", "Consolas", monospace`
  while (ctx.measureText(timeText).width > maxTextWidth && fontSize > 11) {
    fontSize -= 1
    ctx.font = `800 ${fontSize}px "Arial", "DIN Alternate", "Consolas", monospace`
  }
  ctx.fillText(timeText, rect.x + rect.width / 2, rect.y + rect.height * 0.52)
  ctx.restore()
}

async function renderJudgeStage() {
  const canvas = judgeStageCanvasRef.value
  if (!canvas) return

  const image = await loadJudgeStageSourceImage().catch(() => null)
  if (!image) return

  const context = canvas.getContext('2d')
  if (!context) return

  context.clearRect(0, 0, judgeStageSceneSize.width, judgeStageSceneSize.height)
  context.drawImage(image, 0, 0, judgeStageSceneSize.width, judgeStageSceneSize.height)
  drawTimerCutout(context, image)
}

const candidateLabel = computed(() => {
  const raw = String(route.query.candidateNo || '01').trim()
  const normalized = /^\d+$/.test(raw) ? raw.padStart(2, '0') : raw
  return `${normalized}号考生`
})

const isJiangsuFullExamTiming = computed(() => examStore.fullExamMode && examStore.questionList.some((question) => (
  question?.fullExamTimingMode === JIANGSU_FULL_EXAM_TIMING_MODE
)))
const answerDurationSeconds = computed(() => {
  if (isJiangsuFullExamTiming.value) return JIANGSU_ANSWER_SECONDS
  return examStore.questionList.reduce((sum, question) => {
    const answer = Math.max(60, Number(question?.answerTime) || 300)
    return sum + answer
  }, 0)
})
const totalDurationSeconds = computed(() => (
  isJiangsuFullExamTiming.value
    ? JIANGSU_READING_SECONDS + JIANGSU_ANSWER_SECONDS
    : answerDurationSeconds.value
))

const totalDurationMinutes = computed(() => Math.max(1, Math.ceil(totalDurationSeconds.value / 60)))
const timingSummary = computed(() => {
  if (isJiangsuFullExamTiming.value) return `共 ${examStore.totalQuestions} 题，5 分钟阅读，15 分钟作答`
  return `共 ${examStore.totalQuestions} 题，总时长 ${totalDurationMinutes.value} 分钟`
})
const formattedTotalRemaining = computed(() => formatClock(totalRemainingSeconds.value))
const finalAnalysisText = computed(() => examStore.submitStepText || '正在分析结果，请稍候...')
const readingRemainingSeconds = computed(() => {
  if (!isJiangsuFullExamTiming.value || !readingPhaseActive.value) return 0
  return Math.max(0, totalRemainingSeconds.value - JIANGSU_ANSWER_SECONDS)
})
const nextPendingIndex = computed(() => Math.min(examStore.answers.length, Math.max(examStore.totalQuestions - 1, 0)))
const allAnswered = computed(() => examStore.answers.length >= examStore.totalQuestions && examStore.totalQuestions > 0)
const currentAnswer = computed(() => examStore.currentAnswer)
const isViewingPastAnsweredQuestion = computed(() => {
  if (!currentAnswer.value) return false
  return examStore.currentIndex < examStore.answers.length
})
const isAnsweringActiveQuestion = computed(() => (
  examStarted.value
  && examStore.status === EXAM_STATUS.ANSWERING
  && examStore.currentIndex === examStore.answers.length
))

const openingSpeechText = computed(() => (
  `${candidateLabel.value}，请就座。欢迎参加今天的面试，希望通过交流增进对你的了解。`
  + (isJiangsuFullExamTiming.value
    ? `本次面试共有 ${examStore.totalQuestions} 道题目，先阅读五分钟，再作答十五分钟。阅读结束后请开始作答。`
    : `本次面试共有 ${examStore.totalQuestions} 道题目，时间为 ${totalDurationMinutes.value} 分钟。请开始作答。`)
))

const examinerNotice = computed(() => {
  if (!examStarted.value) return openingSpeechText.value
  if (readingPhaseActive.value) return `现在是题本阅读时间，剩余 ${formatClock(readingRemainingSeconds.value)}，请先通读四道题。`
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
  if (!examStarted.value) return '等待开场'
  if (readingPhaseActive.value) return '阅读题本中'
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
  if (!examStarted.value) return { text: '待开始', color: 'blue' }
  if (examStore.status === EXAM_STATUS.ANSWERING) return { text: '作答中', color: 'processing' }
  if (examStore.status === EXAM_STATUS.SUBMITTING) return { text: '评分中', color: 'warning' }
  return { text: '待作答', color: 'gold' }
})

const currentQuestionHint = computed(() => {
  if (!examStarted.value) return '开场引导语播放完成后，点击开始作答即可进入真实考场节奏。'
  if (readingPhaseActive.value) return '江苏模式为 5+15：当前仅阅读题本，阅读倒计时结束后再开始录制作答。'
  if (allAnswered.value) return '所有题目均已提交，可以结束本场全真模拟。'
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
  const storedStream = examStore.consumeStream()
  if (storedStream) {
    recorder.setStream(storedStream)
  } else {
    await recorder.initStream({ videoEnabled: examStore.videoEnabled })
  }

  examStore.goToQuestion(0)
  totalRemainingSeconds.value = totalDurationSeconds.value

  await nextTick()
  renderJudgeStage()
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

watch(formattedTotalRemaining, () => {
  renderJudgeStage()
})

function formatClock(totalSeconds = 0) {
  const safe = Math.max(0, Number(totalSeconds) || 0)
  const minutes = Math.floor(safe / 60)
  const seconds = safe % 60
  return `${String(minutes).padStart(2, '0')}:${String(seconds).padStart(2, '0')}`
}

function isAnsweredQuestion(index) {
  return examStore.answers.some((item) => item.questionIndex === index)
}

function isFutureQuestion(index) {
  return index > examStore.answers.length
}

function questionStatusText(index) {
  if (isAnsweredQuestion(index)) return '已作答'
  if (index === examStore.answers.length) return examStarted.value ? '当前作答位' : '待开始'
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
    message.warning('请先提交当前正在作答的答案。')
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
  if (examStarted.value && !forceReplay) return

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

function beginExam() {
  if (examStarted.value) return
  stopSpeech()
  examStarted.value = true
  readingPhaseActive.value = isJiangsuFullExamTiming.value
  examStore.examStartTime = Date.now()
  examStore.goToQuestion(0)
  totalRemainingSeconds.value = totalDurationSeconds.value
  startTotalTimer()
}

function startTotalTimer() {
  stopTotalTimer()
  totalTimer = setInterval(() => {
    if (submittingAnswer.value) return
    const elapsed = Math.floor((Date.now() - examStore.examStartTime) / 1000)
    totalRemainingSeconds.value = Math.max(0, totalDurationSeconds.value - elapsed)
    if (isJiangsuFullExamTiming.value && readingPhaseActive.value && elapsed >= JIANGSU_READING_SECONDS) {
      readingPhaseActive.value = false
      message.info('阅读时间结束，进入 15 分钟作答阶段。')
    }
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
  if (!examStarted.value) {
    beginExam()
    return
  }
  if (readingPhaseActive.value) {
    message.warning('当前仍在 5 分钟阅读阶段，请阅读结束后再开始作答。')
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
  examStore.startAnswering()
  recorder.startRecording()
}

async function submitCurrentAnswer(options = {}) {
  const { finishAfterSubmit = false } = options

  if (finishRequested.value || submittingAnswer.value || exitingExam.value || examStore.status !== EXAM_STATUS.ANSWERING) return
  submittingAnswer.value = true
  const captureStartedAt = Date.now()
  let captureFinalized = false

  try {
    const usageSeconds = Math.max(1, Math.ceil(Number(recorderDuration.value) || 0))
    const blob = await recorder.stopRecording()
    examStore.examStartTime += Date.now() - captureStartedAt
    captureFinalized = true
    const answer = await examStore.submitAnswer(blob)
    void syncUsage(answer, usageSeconds)

    if (finishAfterSubmit || totalRemainingSeconds.value <= 0 || examStore.answers.length >= examStore.totalQuestions) {
      await finishExam()
    } else {
      examStore.goToQuestion(nextPendingIndex.value)
      message.success('本题已暂存，后台处理中。可以继续下一题。')
    }
  } catch (error) {
    message.error(`提交失败：${error?.message || '未知错误'}`)
  } finally {
    if (!captureFinalized) examStore.examStartTime += Date.now() - captureStartedAt
    submittingAnswer.value = false
  }
}

async function submitCurrentAnswerForExit() {
  if (examStore.status !== EXAM_STATUS.ANSWERING) return null
  const usageSeconds = Math.max(1, Math.ceil(Number(recorderDuration.value) || 0))
  const blob = await recorder.stopRecording()
  if (!blob || blob.size <= 0) return null
  const answer = await examStore.submitAnswer(blob)
  void syncUsage(answer, usageSeconds)
  return answer
}

async function syncUsage(answer, usageSeconds) {
  if (!answer?.examId || !answer?.questionId) return
  try {
    const result = await reportUsage({
      examId: answer.examId,
      questionId: answer.questionId,
      usageSeconds,
      usageType: 'full_exam'
    })
    billingStore.$patch({
      remainingMinutes: Math.max(0, Number(result?.remainingMinutes ?? 0)),
      remainingDailyMinutes: Math.max(0, Number(result?.remainingDailyMinutes ?? 0)),
      usedMinutes: Math.max(0, Number(result?.usedMinutes ?? billingStore.usedMinutes)),
      dailyLimitMinutes: Math.max(0, Number(result?.dailyLimitMinutes ?? billingStore.dailyLimitMinutes))
    })
    billingStore.persist()
  } catch (error) {
    logger.warn('Usage report failed', {
      component: 'FullExamRoom',
      examId: answer.examId,
      questionId: answer.questionId,
      error: error?.message
    })
  }
}

async function handleTimeUp() {
  message.warning('总计时结束，系统将结束本场全真模拟。')

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

  void examStore.finish()

  recorder.destroyStream()
  router.push(`/result/${examId}`)
}

async function exitExam() {
  if (exitingExam.value || finishRequested.value || submittingAnswer.value) return
  exitingExam.value = true
  stopTotalTimer()
  stopSpeech()

  const examId = examStore.examId
  try {
    await submitCurrentAnswerForExit()
  } catch (error) {
    logger.error('Full exam exit submit failed', {
      event: 'full_exam.exit.submit_failed',
      exam_id: examId,
      error
    })
    message.error(`中断提交失败：${error?.message || '未知错误'}`)
    exitingExam.value = false
    return
  }

  if (examId && examStore.answers.length > 0) {
    void examStore.finish()
    recorder.destroyStream()
    router.push(`/result/${examId}`)
    return
  }

  recorder.destroyStream()
  examStore.exitExam()
  router.push('/')
}
</script>

<style scoped>
.full-exam-room { min-height: 100vh; padding: 24px max(24px, calc((100vw - 1440px) / 2)); background: #f7f9fd; color: #203047; }
.full-exam-room__topbar, .full-exam-room__topbar-left, .full-exam-room__topbar-right, .full-exam-room__section-head, .candidate-seat__head, .candidate-panel__head { display: flex; align-items: center; justify-content: space-between; gap: 16px; flex-wrap: wrap; }
.full-exam-room__topbar { margin-bottom: 24px; }
.full-exam-room__badge { display: inline-flex; align-items: center; gap: 8px; background: #eaf8f3; color: #147d74; padding: 10px 16px; border-radius: 12px; font-weight: 700; }
.full-exam-room__meta { color: #596a80; font-size: 14px; }
.full-exam-room__timer { display: flex; align-items: center; gap: 12px; padding: 10px 16px; background: #edf3ff; color: #285bc7; border-radius: 12px; }
.full-exam-room__timer-label { display: block; font-size: 12px; color: #596a80; }
.full-exam-room__timer strong { display: block; font-size: 22px; font-variant-numeric: tabular-nums; }
.full-exam-room__exit { color: #596a80; }
.full-exam-room__offline-banner { padding: 12px 16px; margin-bottom: 16px; background: #fff1e8; color: #a94b2b; border-radius: 12px; }
.card-shell { background: #fdfefe; border: 1px solid #dbe3ee; border-radius: 12px; }
.full-exam-room__judges { padding: 24px; }
.section-kicker { color: #147d74; font-size: 13px; font-weight: 600; }
.full-exam-room__section-head h2 { margin: 6px 0 0; font-size: 24px; }
.full-exam-room__section-head h3, .candidate-seat__head h3, .candidate-panel__head h3 { margin: 6px 0 0; font-size: 18px; }
.full-exam-room__replay { color: #285bc7; }
.judge-speech { display: flex; align-items: flex-start; gap: 16px; margin-top: 20px; }
.judge-speech__avatar { display: grid; place-items: center; width: 44px; height: 44px; flex: 0 0 auto; border-radius: 12px; background: #eaf8f3; color: #147d74; font-size: 24px; }
.judge-speech__content { flex: 1; min-width: 0; }
.judge-speech__title { font-size: 14px; font-weight: 600; color: #596a80; }
.judge-speech__content p { color: #203047; line-height: 1.8; margin: 8px 0 12px; }
.judge-speech__hint { color: #596a80; font-size: 14px; }
.judge-stage { margin: 20px 0 0; border-top: 1px solid #dbe3ee; padding-top: 12px; }
.judge-stage summary { min-height: 44px; display: list-item; align-content: center; color: #596a80; font-size: 14px; cursor: pointer; }
.judge-stage__scene { max-width: 720px; margin: 12px auto 0; }
.judge-stage__canvas { display: block; width: 100%; height: auto; border-radius: 12px; }
.full-exam-room__workspace { display: grid; grid-template-columns: minmax(0, 1.4fr) minmax(320px, .8fr); gap: 24px; margin-top: 24px; align-items: start; }
.full-exam-room__questions { padding: 24px; min-width: 0; }
.question-progress { display: flex; flex-direction: column; gap: 6px; font-size: 13px; color: #596a80; }
.question-progress strong { color: #285bc7; font-weight: 600; }
.question-strip { display: flex; gap: 16px; overflow-x: auto; scroll-snap-type: x proximity; padding: 20px 0 12px; }
.question-card { flex: 0 0 calc(100% - 20px); min-width: 0; padding: 24px; border: 1px solid #dbe3ee; border-radius: 12px; background: #f7f9fd; scroll-snap-align: start; cursor: pointer; transition: border-color 120ms ease; }
.question-card.is-current { background: #fdfefe; border-color: #285bc7; }
.question-card.is-answered .question-card__status { color: #147d74; background: #eaf8f3; }
.question-card__top { display: flex; gap: 12px; align-items: center; justify-content: space-between; margin-bottom: 16px; font-size: 14px; }
.question-card__index { font-weight: 700; color: #203047; }
.question-card__status { padding: 4px 8px; background: #edf3ff; color: #285bc7; border-radius: 6px; }
.question-card__stem { margin-top: 20px; }
.question-card__stem :deep(.question-rich-content__body) { color: #203047; font-size: 17px; line-height: 1.85; }
.question-nav { display: flex; justify-content: space-between; gap: 12px; margin-top: 12px; }
.full-exam-room__candidate { min-width: 0; }
.candidate-stack { display: flex; flex-direction: column; gap: 16px; }
.candidate-seat, .candidate-panel { padding: 20px; }
.candidate-seat__status { font-size: 13px; color: #596a80; padding: 6px 10px; border-radius: 8px; background: #f7f9fd; }
.candidate-seat__status.is-recording { color: #147d74; background: #eaf8f3; }
.candidate-seat__video { margin-top: 16px; border-radius: 12px; overflow: hidden; max-height: 250px; background: #203047; }
.candidate-seat__video :deep(video) { max-height: 250px; }
.candidate-seat__wave { margin-top: 12px; overflow: hidden; }
.candidate-panel__head-side { display: flex; align-items: center; gap: 8px; flex-wrap: wrap; }
.candidate-panel__inline-timer { display: flex; gap: 6px; color: #285bc7; font-variant-numeric: tabular-nums; font-size: 14px; }
.candidate-panel__question { margin-top: 20px; padding-top: 16px; border-top: 1px solid #dbe3ee; }
.candidate-panel__question-body { margin-top: 12px; color: #203047; }
.candidate-panel__question-body :deep(.question-rich-content__body) { color: #203047; font-size: 16px; line-height: 1.8; }
.candidate-panel__hint { font-size: 14px; line-height: 1.7; color: #596a80; margin: 16px 0; }
.candidate-panel__analysis, .candidate-panel__summary { padding: 12px; background: #edf3ff; border-radius: 12px; margin: 12px 0; line-height: 1.7; font-size: 14px; }
.candidate-panel__actions { display: flex; flex-direction: column; gap: 12px; }
.candidate-panel__actions > .background-answers { margin: 0; }
.full-exam-room--empty { display: grid; align-content: center; justify-items: center; }
@media (max-width: 960px) {
  .full-exam-room { padding: 20px; }
  .full-exam-room__workspace { grid-template-columns: 1fr; }
  .candidate-stack { display: grid; grid-template-columns: minmax(0, 1fr) minmax(0, 1fr); }
}
@media (max-width: 600px) {
  .full-exam-room { padding: 16px; }
  .full-exam-room__topbar { gap: 12px; }
  .full-exam-room__topbar-right { width: 100%; }
  .full-exam-room__judges, .full-exam-room__questions { padding: 16px; }
  .full-exam-room__section-head h2 { font-size: 20px; }
  .judge-speech__avatar { display: none; }
  .candidate-stack { display: flex; }
  .question-card { padding: 16px; flex-basis: calc(100% - 12px); }
}
</style>
<style src="@/styles/learner.css"></style>
