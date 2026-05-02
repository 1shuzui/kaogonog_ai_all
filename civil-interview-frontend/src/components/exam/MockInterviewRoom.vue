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
      <div class="mock-room__banner" :data-year="currentYearLabel">
        <span class="mock-room__banner-prefix">2025 年度</span>
        <strong>公务员结构化面试模拟现场</strong>
      </div>

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

      <div class="judge-stage">
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
          <QuestionMetaTags :question="question" emphasis compact :max-keywords="4" />
          <div class="question-card__stem">
            <QuestionRichContent
              :text="question.stem"
              compact
              :collapsed-height="156"
            />
          </div>
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

        <div class="candidate-panel__question">
          <QuestionMetaTags :question="examStore.currentQuestion" emphasis :max-keywords="6" />
          <div class="candidate-panel__question-body">
            <QuestionRichContent
              :text="examStore.currentQuestion?.stem || ''"
              dark
              scrollable
              :scroll-height="220"
              :collapsed-height="170"
            />
          </div>
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
import { DIMENSIONS, EXAM_STATUS, getQuestionTypeName } from '@/utils/constants'
import AudioWaveform from '@/components/recording/AudioWaveform.vue'
import VideoPreview from '@/components/recording/VideoPreview.vue'
import QuestionMetaTags from '@/components/common/QuestionMetaTags.vue'
import QuestionRichContent from '@/components/common/QuestionRichContent.vue'
import mockRoomBg from '@/assets/exam/mock-interview-ai-clean.jpg'
import judgeRoomReferenceOriginal from '@/assets/exam/mock-interview-room-live.jpg'
import judgeRoomReferenceStage2026 from '@/assets/exam/mock-interview-room-stage-2026.jpg'

const router = useRouter()
const route = useRoute()
const examStore = useExamStore()
const recorder = useMediaRecorder()
const { isOnline } = useNetworkStatus()

const stream = recorder.stream
const recorderDuration = recorder.duration
const questionStripRef = ref(null)
const judgeStageCanvasRef = ref(null)
const judgeStageSceneSize = { width: 720, height: 404 }

const mockStarted = ref(false)
const speechInProgress = ref(false)
const totalRemainingSeconds = ref(0)
const finishRequested = ref(false)
const currentYearLabel = `${new Date().getFullYear()}年度`
const bakedJudgeRoomYearLabel = '2026年度'
const useBakedJudgeStage = computed(() => currentYearLabel === bakedJudgeRoomYearLabel)
const judgeRoomReference = computed(() => (
  useBakedJudgeStage.value ? judgeRoomReferenceStage2026 : judgeRoomReferenceOriginal
))
let totalTimer = null
let speechUtterance = null
const judgeStageSourceImageCache = new Map()
const judgeStageSourceImagePromiseCache = new Map()
const judgeStageViewport = {
  sourceX: 175,
  sourceWidth: 545
}

const judgeTimerPanelConfig = {
  x: 686,
  y: 284,
  width: 56,
  height: 36,
  rotate: 0
}

function loadJudgeStageSourceImage() {
  const src = judgeRoomReference.value
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

function drawRoundedRect(ctx, x, y, width, height, radius) {
  const safeRadius = Math.min(radius, width / 2, height / 2)
  ctx.beginPath()
  ctx.moveTo(x + safeRadius, y)
  ctx.lineTo(x + width - safeRadius, y)
  ctx.quadraticCurveTo(x + width, y, x + width, y + safeRadius)
  ctx.lineTo(x + width, y + height - safeRadius)
  ctx.quadraticCurveTo(x + width, y + height, x + width - safeRadius, y + height)
  ctx.lineTo(x + safeRadius, y + height)
  ctx.quadraticCurveTo(x, y + height, x, y + height - safeRadius)
  ctx.lineTo(x, y + safeRadius)
  ctx.quadraticCurveTo(x, y, x + safeRadius, y)
  ctx.closePath()
}

function drawYearPatch(ctx, image) {
  const patchX = 0
  const patchY = 58
  const patchWidth = 236
  const patchHeight = 55
  const sampleX = 18
  const sampleY = 59
  const sampleWidth = 40

  ctx.save()
  ctx.drawImage(
    image,
    sampleX,
    sampleY,
    sampleWidth,
    patchHeight,
    patchX,
    patchY,
    patchWidth,
    patchHeight
  )

  const tint = ctx.createLinearGradient(patchX, patchY, patchX + patchWidth, patchY)
  tint.addColorStop(0, 'rgba(148, 12, 9, 0.22)')
  tint.addColorStop(0.5, 'rgba(198, 39, 20, 0.12)')
  tint.addColorStop(1, 'rgba(150, 12, 9, 0.2)')
  ctx.fillStyle = tint
  ctx.fillRect(patchX, patchY, patchWidth, patchHeight)

  ctx.fillStyle = '#7f1710'
  ctx.textAlign = 'left'
  ctx.textBaseline = 'middle'
  ctx.font = '700 30px "Microsoft YaHei", "PingFang SC", sans-serif'
  ctx.fillText(currentYearLabel, patchX + 22, patchY + patchHeight / 2 + 2)

  ctx.fillStyle = '#fff5e7'
  ctx.shadowColor = 'rgba(96, 17, 9, 0.22)'
  ctx.shadowBlur = 2
  ctx.fillText(currentYearLabel, patchX + 19, patchY + patchHeight / 2)
  ctx.restore()
}

function drawTimerPanel(ctx) {
  const { x, y, width, height, rotate } = judgeTimerPanelConfig

  ctx.save()
  ctx.translate(x, y)
  ctx.rotate(rotate * Math.PI / 180)

  ctx.fillStyle = 'rgba(32, 18, 9, 0.16)'
  drawRoundedRect(ctx, -width / 2 + 1.5, -height / 2 + 3, width - 2, height - 2, 4)
  ctx.fill()

  const panelGradient = ctx.createLinearGradient(0, -height / 2, 0, height / 2)
  panelGradient.addColorStop(0, 'rgba(180, 158, 118, 0.96)')
  panelGradient.addColorStop(1, 'rgba(129, 104, 68, 0.96)')
  ctx.fillStyle = panelGradient
  ctx.strokeStyle = 'rgba(87, 63, 35, 0.34)'
  ctx.lineWidth = 0.8
  drawRoundedRect(ctx, -width / 2, -height / 2, width, height, 4)
  ctx.fill()
  ctx.stroke()

  ctx.fillStyle = 'rgba(78, 54, 28, 0.94)'
  ctx.textAlign = 'center'
  ctx.textBaseline = 'middle'
  ctx.font = '600 7px "SimSun", "Songti SC", serif'
  ctx.fillText('计时员', 0, -height / 2 + 6)

  drawRoundedRect(ctx, -width / 2 + 6, -5, width - 12, 20, 3)
  ctx.fillStyle = 'rgba(26, 31, 27, 0.98)'
  ctx.fill()
  ctx.strokeStyle = 'rgba(220, 235, 210, 0.12)'
  ctx.lineWidth = 0.6
  ctx.stroke()

  ctx.fillStyle = '#d9ffd4'
  ctx.font = '700 11px "Consolas", "Courier New", monospace'
  ctx.fillText(formattedTotalRemaining.value, 0, 4)
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
  if (useBakedJudgeStage.value) {
    context.drawImage(image, 0, 0, judgeStageSceneSize.width, judgeStageSceneSize.height)
  } else {
    const { sourceX, sourceWidth } = judgeStageViewport
    context.drawImage(image, sourceX, 0, sourceWidth, image.height, 0, 0, judgeStageSceneSize.width, judgeStageSceneSize.height)
    drawYearPatch(context, image)
  }
  drawTimerPanel(context)
}

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

function getDimensionLabel(key) {
  return getQuestionTypeName(key) || DIMENSIONS.find((item) => item.key === key)?.name || key || '结构化面试题'
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
  examStore.startAnswering()
  recorder.startRecording()
}

async function submitCurrentAnswer(options = {}) {
  const { finishAfterSubmit = false } = options

  if (examStore.status !== EXAM_STATUS.ANSWERING) return

  try {
    const blob = await recorder.stopRecording()
    if (!blob) return

    await examStore.submitAnswer(blob)

    if (finishAfterSubmit || totalRemainingSeconds.value <= 0) {
      await finishExam()
    }
  } catch (error) {
    message.error(`提交失败：${error?.message || '未知错误'}`)
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
    await examStore.evaluatePendingAnswers()
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
      await examStore.waitForPendingProcessing()
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
  padding: 18px 20px 22px;
  color: #fff;
  overflow: hidden;
  background: #342218;
}

.mock-room__bg,
.mock-room__overlay {
  position: fixed;
  inset: 0;
  pointer-events: none;
}

.mock-room__bg {
  background-position: center 8%;
  background-size: cover;
  filter: saturate(0.96) contrast(1.01) brightness(0.8);
  transform: scale(1.015);
}

.mock-room__overlay {
  background:
    linear-gradient(180deg, rgba(42, 25, 17, 0.08) 0%, rgba(103, 72, 43, 0.1) 22%, rgba(81, 55, 35, 0.24) 46%, rgba(58, 37, 25, 0.6) 72%, rgba(41, 25, 18, 0.9) 100%),
    radial-gradient(circle at 26% 4%, rgba(255, 220, 152, 0.38), transparent 20%),
    radial-gradient(circle at 50% 2%, rgba(255, 224, 163, 0.42), transparent 24%),
    radial-gradient(circle at 74% 4%, rgba(255, 220, 152, 0.38), transparent 20%),
    repeating-linear-gradient(90deg, rgba(142, 108, 74, 0.12) 0 1px, transparent 1px 16.66%);
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
  margin-bottom: 18px;
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
  background: rgba(249, 240, 225, 0.88);
  border: 1px solid rgba(112, 70, 36, 0.18);
  color: #5a351d;
  box-shadow: 0 10px 20px rgba(44, 23, 12, 0.16);
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
  background: rgba(74, 37, 22, 0.84);
  border: 1px solid rgba(255, 229, 191, 0.18);
  box-shadow: 0 12px 26px rgba(35, 17, 10, 0.2);

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
  border-radius: 24px;
  border: 1px solid rgba(116, 74, 36, 0.18);
  background: rgba(248, 242, 232, 0.9);
  box-shadow:
    inset 0 1px 0 rgba(255, 250, 240, 0.72),
    0 20px 44px rgba(34, 18, 10, 0.2);
  backdrop-filter: blur(4px);
}

.mock-room__judges {
  position: relative;
  display: flex;
  flex-direction: column;
  justify-content: space-between;
  min-height: 50vh;
  padding: 34px 30px 30px;
  background:
    linear-gradient(180deg, rgba(249, 240, 222, 0.24) 0%, rgba(242, 226, 197, 0.08) 30%, rgba(86, 53, 33, 0.14) 100%);
  border-color: rgba(255, 248, 233, 0.26);
  overflow: hidden;
}

.mock-room__judges::before {
  content: '';
  position: absolute;
  inset: 0;
  background:
    linear-gradient(180deg, rgba(255, 248, 233, 0.12) 0%, transparent 34%, rgba(128, 83, 52, 0.08) 34%, rgba(128, 83, 52, 0.08) 64%, transparent 64%),
    radial-gradient(circle at 26% 5%, rgba(255, 222, 153, 0.34), transparent 20%),
    radial-gradient(circle at 50% 3%, rgba(255, 224, 163, 0.38), transparent 22%),
    radial-gradient(circle at 74% 5%, rgba(255, 222, 153, 0.34), transparent 20%),
    repeating-linear-gradient(90deg, rgba(145, 103, 70, 0.12) 0 1px, transparent 1px 16.66%);
  pointer-events: none;
}

.mock-room__judges::after {
  content: '';
  position: absolute;
  left: 0;
  right: 0;
  bottom: 0;
  height: 120px;
  background:
    linear-gradient(180deg, rgba(97, 60, 34, 0) 0%, rgba(97, 60, 34, 0.22) 28%, rgba(67, 39, 23, 0.34) 100%),
    linear-gradient(90deg, rgba(89, 54, 31, 0.22) 0%, rgba(157, 116, 76, 0.1) 14%, rgba(157, 116, 76, 0.1) 86%, rgba(89, 54, 31, 0.22) 100%);
  border-top: 1px solid rgba(255, 233, 197, 0.12);
  pointer-events: none;
}

.mock-room__judges > * {
  position: relative;
  z-index: 1;
}

.mock-room__workspace {
  display: grid;
  grid-template-columns: minmax(0, 1.48fr) minmax(360px, 0.84fr);
  gap: 20px;
  align-items: stretch;
  margin-top: -14px;
}

.mock-room__questions {
  position: relative;
  padding: 22px;
  background: linear-gradient(180deg, rgba(147, 95, 58, 0.96) 0%, rgba(112, 67, 38, 0.98) 56%, rgba(84, 49, 28, 0.98) 100%);
  box-shadow: 0 24px 36px rgba(43, 21, 11, 0.22);
}

.mock-room__questions::before {
  content: '';
  position: absolute;
  inset: 12px 14px 16px;
  border-radius: 18px;
  background: linear-gradient(180deg, rgba(255, 252, 245, 0.97) 0%, rgba(241, 231, 209, 0.96) 100%);
  border: 1px solid rgba(132, 91, 49, 0.16);
  box-shadow: inset 0 1px 0 rgba(255, 255, 255, 0.84);
  pointer-events: none;
}

.mock-room__questions > * {
  position: relative;
  z-index: 1;
}

.mock-room__candidate {
  min-width: 0;
}

.candidate-stack {
  position: relative;
  display: grid;
  gap: 16px;
  padding: 18px 16px 22px;
}

.candidate-stack::before {
  content: '';
  position: absolute;
  inset: 0;
  border-radius: 28px;
  background: linear-gradient(180deg, rgba(155, 99, 57, 0.96) 0%, rgba(118, 70, 39, 0.98) 52%, rgba(82, 47, 27, 0.98) 100%);
  box-shadow: 0 22px 36px rgba(38, 20, 11, 0.22);
}

.candidate-stack::after {
  content: '';
  position: absolute;
  left: 16px;
  right: 16px;
  bottom: -8px;
  height: 20px;
  border-radius: 0 0 16px 16px;
  background: linear-gradient(180deg, rgba(90, 52, 31, 0.94) 0%, rgba(54, 30, 18, 0.9) 100%);
  pointer-events: none;
}

.candidate-stack > * {
  position: relative;
  z-index: 1;
}

.candidate-seat,
.candidate-panel {
  position: relative;
  overflow: hidden;
  padding: 20px;
}

.candidate-seat {
  background: linear-gradient(180deg, rgba(252, 248, 240, 0.98) 0%, rgba(232, 214, 183, 0.96) 100%);
  border: 1px solid rgba(118, 78, 42, 0.18);
  box-shadow: 0 18px 28px rgba(43, 22, 11, 0.18);
}

.candidate-panel {
  background: linear-gradient(180deg, rgba(126, 47, 29, 0.96) 0%, rgba(92, 37, 24, 0.96) 36%, rgba(56, 26, 16, 0.96) 100%);
  border: 1px solid rgba(255, 219, 184, 0.1);
  box-shadow: 0 18px 28px rgba(43, 22, 11, 0.22);
}

.mock-room__section-head {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  gap: 12px;
  margin-bottom: 20px;

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

.mock-room__banner {
  display: none;
}

.mock-room__banner::before {
  content: attr(data-year);
  position: relative;
  z-index: 1;
  font-size: 18px;
  font-weight: 700;
  color: rgba(255, 241, 215, 0.96);
  letter-spacing: 1px;
}

.mock-room__banner::after {
  content: '';
  position: absolute;
  inset: 0;
  background:
    radial-gradient(circle at 12% 50%, rgba(255, 255, 255, 0.12), transparent 12%),
    radial-gradient(circle at 50% 50%, rgba(255, 255, 255, 0.1), transparent 18%),
    radial-gradient(circle at 88% 50%, rgba(255, 255, 255, 0.12), transparent 12%),
    linear-gradient(90deg, rgba(112, 9, 7, 0.16) 0%, transparent 16%, transparent 84%, rgba(112, 9, 7, 0.16) 100%);
  opacity: 0.7;
  pointer-events: none;
}

.mock-room__banner-prefix {
  display: none;
}

.mock-room__banner strong {
  position: relative;
  z-index: 1;
  font-size: clamp(30px, 2.6vw, 54px);
  font-weight: 800;
  letter-spacing: 1px;
  color: #fff3df;
  text-shadow: 0 3px 10px rgba(92, 18, 10, 0.24);
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

.mock-room__judges .section-kicker {
  background: rgba(118, 25, 18, 0.82);
  color: rgba(255, 245, 229, 0.94);
}

.mock-room__judges .mock-room__section-head h2 {
  color: #fff6e8;
  text-shadow: 0 5px 18px rgba(51, 20, 9, 0.3);
}

.mock-room__questions .section-kicker {
  background: rgba(115, 76, 40, 0.12);
  color: #704520;
}

.mock-room__questions .mock-room__section-head h3 {
  color: #442816;
}

.mock-room__replay {
  color: rgba(255, 245, 229, 0.92);
  padding: 0 14px;
  border-radius: 999px;
  background: rgba(110, 31, 20, 0.34);
}

.judge-speech {
  display: grid;
  grid-template-columns: 66px minmax(0, 1fr);
  gap: 16px;
  max-width: 900px;
  margin: 18px auto 0;
  padding: 20px 24px;
  border-radius: 18px;
  background: linear-gradient(180deg, rgba(121, 39, 26, 0.92) 0%, rgba(78, 29, 21, 0.88) 100%);
  border: 1px solid rgba(255, 227, 194, 0.14);
  box-shadow: 0 20px 30px rgba(46, 18, 10, 0.24);
}

.judge-speech__avatar {
  display: flex;
  align-items: center;
  justify-content: center;
  font-weight: 700;
}

.judge-speech__avatar {
  width: 66px;
  height: 66px;
  border-radius: 18px;
  background: linear-gradient(180deg, #f9edd4 0%, #dcc18e 100%);
  color: #6c3112;
  font-size: 18px;
  box-shadow: inset 0 1px 0 rgba(255, 255, 255, 0.7);
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
  color: #fff6ea;
  font-size: 19px;
  line-height: 1.75;
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

.judge-stage {
  max-width: 1220px;
  margin: 26px auto 0;
}

.judge-stage__scene {
  position: relative;
  min-height: 0;
  border-radius: 30px 30px 24px 24px;
  overflow: hidden;
  background: rgba(255, 249, 238, 0.96);
  box-shadow:
    inset 0 1px 0 rgba(255, 246, 228, 0.44),
    0 26px 36px rgba(42, 21, 11, 0.24);
  isolation: isolate;
}

.judge-stage__scene::before {
  display: none;
}

.judge-stage__scene::after {
  display: none;
}

.judge-stage__image {
  display: block;
  width: 100%;
  height: auto;
}

.judge-stage__year-fix {
  position: absolute;
  top: 13.5%;
  left: 23%;
  z-index: 3;
  width: 21.4%;
  height: 9.4%;
  transform: translate(-50%, -50%);
  pointer-events: none;
}

.judge-stage__year-mask {
  position: absolute;
  inset: 0;
  border-radius: 1px;
  background: linear-gradient(90deg, rgba(150, 11, 6, 0.95) 0%, rgba(194, 32, 18, 0.93) 52%, rgba(141, 9, 6, 0.95) 100%);
  box-shadow:
    inset 0 1px 0 rgba(255, 196, 162, 0.12),
    inset 0 -1px 0 rgba(103, 2, 1, 0.24);
}

.judge-stage__year-text {
  position: relative;
  z-index: 1;
  display: flex;
  align-items: center;
  justify-content: center;
  width: 100%;
  height: 100%;
  color: #fff6e6;
  font-family: 'Microsoft YaHei', 'PingFang SC', sans-serif;
  text-shadow: 0 1px 2px rgba(74, 8, 4, 0.24);
  white-space: nowrap;
  font-size: clamp(18px, 2.38vw, 31px);
  letter-spacing: 0;
  font-weight: 700;
  line-height: 1;
}

.judge-stage__nameplate {
  position: absolute;
  z-index: 3;
  width: var(--plate-width, 32px);
  height: var(--plate-height, 12px);
  transform: translate(-50%, -50%);
  pointer-events: none;
}

.judge-stage__nameplate-card {
  position: relative;
  display: flex;
  align-items: center;
  justify-content: center;
  width: 100%;
  height: 100%;
  transform: rotate(var(--plate-rotate, 0deg)) skewX(var(--plate-skew, 0deg)) scale(var(--plate-scale, 1));
  transform-origin: center center;
  clip-path: polygon(8% 0, 92% 0, 100% 100%, 0 100%);
  background: linear-gradient(180deg, rgba(254, 250, 241, 0.96) 0%, rgba(236, 223, 194, 0.94) 100%);
  border: 1px solid rgba(126, 100, 61, 0.42);
  box-shadow:
    inset 0 1px 0 rgba(255, 255, 255, 0.72),
    0 1px 2px rgba(56, 31, 15, 0.16);
}

.judge-stage__nameplate-card::before {
  content: '';
  position: absolute;
  left: 10%;
  right: 10%;
  top: 52%;
  border-top: 1px solid rgba(146, 116, 71, 0.1);
}

.judge-stage__nameplate-card::after {
  content: '';
  position: absolute;
  left: 12%;
  right: 10%;
  bottom: -2px;
  height: 3px;
  background: rgba(48, 27, 13, 0.16);
  filter: blur(2px);
  z-index: -1;
  transform: translateX(1px);
}

.judge-stage__nameplate strong {
  position: relative;
  z-index: 1;
  display: block;
  color: rgba(78, 55, 28, 0.92);
  font-family: 'SimSun', 'Songti SC', serif;
  font-size: clamp(7px, 0.62vw, 9px);
  font-weight: 700;
  line-height: 1;
  letter-spacing: 0;
  white-space: nowrap;
  transform: skewX(calc(var(--plate-skew, 0deg) * -1));
}

.judge-stage__nameplate--lead {
  width: var(--plate-width, 40px);
  height: var(--plate-height, 13px);
}

.judge-stage__nameplate--lead .judge-stage__nameplate-card {
  background: linear-gradient(180deg, rgba(255, 251, 243, 0.98) 0%, rgba(242, 225, 188, 0.96) 100%);
  border-color: rgba(142, 98, 48, 0.48);
  box-shadow:
    inset 0 1px 0 rgba(255, 255, 255, 0.8),
    0 1px 2px rgba(56, 31, 16, 0.18);
}

.judge-stage__nameplate--lead strong {
  color: #7a2d19;
  font-size: clamp(7.5px, 0.7vw, 10px);
  font-weight: 800;
}

.judge-stage__timer-panel {
  position: absolute;
  left: 91.4%;
  top: 70.6%;
  z-index: 3;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 2px;
  width: 56px;
  padding: 4px 4px 5px;
  transform: translate(-50%, -50%) rotate(-8deg) skewX(-6deg);
  border-radius: 4px;
  background: linear-gradient(180deg, rgba(170, 145, 98, 0.96) 0%, rgba(129, 105, 62, 0.96) 100%);
  border: 1px solid rgba(95, 70, 37, 0.44);
  box-shadow: 0 3px 6px rgba(38, 21, 11, 0.18);
  text-align: center;
  pointer-events: none;
}

.judge-stage__timer-panel::after {
  content: '';
  position: absolute;
  left: 14%;
  right: 12%;
  bottom: -3px;
  height: 3px;
  background: rgba(41, 22, 11, 0.16);
  filter: blur(2px);
  z-index: -1;
}

.judge-stage__timer-tag {
  color: #4f3617;
  font-family: 'SimSun', 'Songti SC', serif;
  font-size: 8px;
  font-weight: 700;
  letter-spacing: 0;
  transform: skewX(6deg);
}

.judge-stage__timer-readout {
  display: block;
  width: 100%;
  padding: 3px 4px;
  border-radius: 3px;
  background: linear-gradient(180deg, rgba(24, 30, 24, 0.98) 0%, rgba(46, 56, 45, 0.98) 100%);
  border: 1px solid rgba(223, 236, 211, 0.18);
  box-shadow: inset 0 1px 0 rgba(255, 255, 255, 0.12);
  color: #d8ffd4;
  font-family: 'Consolas', 'Courier New', monospace;
  font-size: clamp(10px, 0.94vw, 14px);
  line-height: 1;
  letter-spacing: 0.6px;
  font-variant-numeric: tabular-nums;
  transform: skewX(6deg);
}

.judge-stage__timer-panel small {
  color: rgba(73, 49, 20, 0.84);
  font-size: 7px;
  letter-spacing: 0;
  line-height: 1;
  transform: skewX(6deg);
}

.question-progress {
  display: flex;
  flex-direction: column;
  align-items: flex-end;
  gap: 4px;
  color: rgba(74, 48, 27, 0.76);
  font-size: @font-size-sm;

  strong {
    color: #4d2d18;
  }
}

.question-strip {
  display: grid;
  grid-auto-flow: column;
  grid-auto-columns: minmax(320px, 35vw);
  gap: 18px;
  overflow-x: auto;
  padding: 18px 16px 22px;
  border-radius: 20px;
  background: linear-gradient(180deg, rgba(153, 105, 64, 0.12) 0%, rgba(255, 255, 255, 0.08) 100%);
  box-shadow: inset 0 0 0 1px rgba(125, 84, 47, 0.12);
  scroll-snap-type: x mandatory;
  perspective: 1200px;
}

.question-strip::-webkit-scrollbar {
  height: 8px;
}

.question-strip::-webkit-scrollbar-thumb {
  border-radius: 999px;
  background: rgba(95, 62, 36, 0.24);
}

.question-card {
  --paper-tilt: 0deg;
  scroll-snap-align: start;
  position: relative;
  min-height: 232px;
  padding: 18px 18px 20px;
  border-radius: 18px;
  border: 1px solid rgba(116, 77, 38, 0.16);
  background: linear-gradient(180deg, rgba(255, 253, 247, 0.98) 0%, rgba(246, 236, 214, 0.97) 100%);
  box-shadow:
    inset 0 1px 0 rgba(255, 255, 255, 0.82),
    0 14px 24px rgba(81, 48, 25, 0.14);
  cursor: pointer;
  transition: transform 0.22s ease, border-color 0.22s ease, box-shadow 0.22s ease;
  transform: rotate(var(--paper-tilt));
}

.question-card:nth-child(odd) {
  --paper-tilt: -0.7deg;
}

.question-card:nth-child(even) {
  --paper-tilt: 0.55deg;
}

.question-card::before {
  content: '';
  position: absolute;
  left: 20px;
  right: 20px;
  top: 60px;
  bottom: 20px;
  background: repeating-linear-gradient(
    180deg,
    transparent 0,
    transparent 27px,
    rgba(133, 104, 73, 0.08) 27px,
    rgba(133, 104, 73, 0.08) 28px
  );
  pointer-events: none;
  opacity: 0.9;
}

.question-card::after {
  content: '';
  position: absolute;
  top: 0;
  right: 0;
  width: 34px;
  height: 34px;
  background: linear-gradient(225deg, rgba(212, 189, 154, 0.94) 0%, rgba(246, 236, 214, 0.24) 100%);
  clip-path: polygon(0 0, 100% 0, 100% 100%);
  border-top-right-radius: 18px;
}

.question-card > * {
  position: relative;
  z-index: 1;
}

.question-card:hover {
  transform: translateY(-4px) rotate(var(--paper-tilt));
}

.question-card.is-current {
  border-color: rgba(147, 48, 27, 0.52);
  box-shadow: 0 18px 30px rgba(75, 39, 18, 0.16);
  transform: translateY(-6px) rotate(0deg);
}

.question-card.is-answered {
  background: linear-gradient(180deg, rgba(236, 246, 235, 0.98) 0%, rgba(214, 232, 206, 0.96) 100%);
  border-color: rgba(84, 141, 92, 0.22);
}

.question-card.is-pending {
  background: linear-gradient(180deg, rgba(255, 248, 227, 0.98) 0%, rgba(244, 226, 187, 0.96) 100%);
  border-color: rgba(178, 121, 41, 0.22);
}

.question-card.is-future {
  opacity: 0.8;
}

.question-card__top,
.question-card__meta {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 10px;
}

.question-card__top {
  padding-bottom: 10px;
  border-bottom: 1px dashed rgba(115, 76, 40, 0.26);
}

.question-card__index,
.question-card__status,
.question-card__meta {
  font-size: @font-size-xs;
  color: rgba(90, 58, 34, 0.78);
}

.question-card__status {
  padding: 4px 8px;
  border-radius: 999px;
  background: rgba(95, 62, 36, 0.08);
}

.question-card__stem {
  margin: 12px 0 18px;
}

.question-card__stem :deep(.question-rich-content__body) {
  color: #2f2319;
}

.question-card__stem :deep(.question-rich-content__paragraph) {
  font-size: 16px;
  line-height: 1.85;
}

.question-nav {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 10px;
  margin-top: 14px;
  padding-top: 12px;
  border-top: 1px solid rgba(120, 81, 46, 0.16);
}

.mock-room__questions::after,
.candidate-seat::after,
.candidate-panel::after {
  content: '';
  position: absolute;
  left: 14px;
  right: 14px;
  bottom: 0;
  height: 10px;
  border-radius: 0 0 18px 18px;
  background: linear-gradient(180deg, #8c5b34 0%, #6a3e20 100%);
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

.candidate-seat__head h3 {
  color: #4a2c18;
}

.candidate-panel__head h3 {
  color: #fff7ec;
}

.candidate-seat__status {
  padding: 6px 12px;
  border-radius: 999px;
  background: rgba(100, 65, 34, 0.12);
  color: #654021;
  font-size: @font-size-xs;
}

.candidate-seat__status.is-recording {
  background: rgba(207, 19, 34, 0.2);
  color: #ffd5d5;
}

.candidate-seat__video {
  aspect-ratio: 4 / 3;
  border-radius: 20px;
  overflow: hidden;
  background: #000;
  border: 10px solid rgba(88, 55, 32, 0.94);
  box-shadow: 0 16px 28px rgba(46, 21, 10, 0.18);
}

.candidate-seat__wave {
  margin-top: 14px;
  padding: 12px 14px;
  border-radius: 16px;
  background: rgba(93, 61, 35, 0.12);
  box-shadow: inset 0 0 0 1px rgba(123, 86, 52, 0.12);
}

.candidate-panel__hint {
  margin: 14px 0 12px;
  color: rgba(255, 244, 232, 0.86);
  line-height: 1.8;
}

.candidate-panel__question {
  margin-top: 12px;
  padding: 14px;
  border-radius: 16px;
  background: rgba(255, 246, 233, 0.08);
  border: 1px solid rgba(255, 226, 195, 0.12);
}

.candidate-panel__question-body {
  margin-top: 10px;
}

.candidate-panel__question-body :deep(.question-rich-content__body) {
  color: rgba(255, 244, 232, 0.92);
}

.candidate-panel__summary {
  padding: 12px 14px;
  border-radius: 16px;
  background: rgba(255, 246, 233, 0.1);
  border: 1px solid rgba(255, 226, 195, 0.14);
  color: rgba(255, 244, 232, 0.78);
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
    margin-top: 12px;
  }

  .judge-stage__scene {
    min-height: 0;
  }

  .judge-stage__year-fix {
    width: 22.4%;
    height: 9.8%;
  }

  .judge-stage__timer-panel {
    left: 91.2%;
    top: 70.2%;
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

  .mock-room__judges {
    padding-top: 28px;
  }

  .judge-stage {
    margin-top: 20px;
  }

  .judge-stage__scene {
    min-height: 0;
  }

  .judge-stage__year-fix {
    top: 13.4%;
    left: 23.2%;
    width: 23.6%;
    height: 9.6%;
  }

  .judge-stage__year-text {
    font-size: clamp(15px, 2.45vw, 24px);
  }

  .judge-stage__nameplate {
    width: calc(var(--plate-width, 32px) * 0.88);
    height: calc(var(--plate-height, 12px) * 0.88);

    strong {
      font-size: clamp(6px, 0.9vw, 8px);
    }
  }

  .judge-stage__nameplate--lead {
    width: calc(var(--plate-width, 40px) * 0.9);
    height: calc(var(--plate-height, 13px) * 0.9);
  }

  .judge-stage__timer-panel {
    left: 91%;
    top: 70%;
    width: 48px;
    padding: 3px 3px 4px;

    .judge-stage__timer-readout {
      font-size: clamp(9px, 1.7vw, 12px);
    }
  }

  .mock-room__banner {
    position: relative;
    top: auto;
    left: auto;
    transform: none;
    justify-content: center;
    min-height: 56px;
    margin-bottom: 16px;
    padding: 0 18px;
  }

  .mock-room__banner strong {
    font-size: 24px;
    letter-spacing: 1px;
  }

  .mock-room__topbar,
  .mock-room__topbar-right {
    flex-direction: column;
    align-items: stretch;
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

  .mock-room__banner {
    flex-direction: column;
    gap: 4px;
  }

  .judge-stage__scene {
    min-height: 0;
    border-radius: 24px 24px 18px 18px;
  }

  .judge-stage__year-fix {
    top: 13.2%;
    left: 23.1%;
    width: 25.4%;
    height: 9.2%;
  }

  .judge-stage__year-text {
    font-size: clamp(10px, 2.8vw, 16px);
    letter-spacing: 0.2px;
  }

  .judge-stage__nameplate {
    width: calc(var(--plate-width, 32px) * 0.72);
    height: calc(var(--plate-height, 12px) * 0.72);

    strong {
      font-size: 6px;
      letter-spacing: 0;
    }
  }

  .judge-stage__nameplate--lead {
    width: calc(var(--plate-width, 40px) * 0.76);
    height: calc(var(--plate-height, 13px) * 0.76);
  }

  .judge-stage__timer-panel {
    left: 90.8%;
    top: 69.6%;
    width: 40px;
    padding: 2px 2px 3px;

    .judge-stage__timer-readout {
      font-size: 8px;
      letter-spacing: 0.3px;
    }

    small,
    .judge-stage__timer-tag {
      font-size: 6px;
    }
  }

  .question-strip {
    padding: 14px 12px 18px;
  }

  .candidate-stack {
    padding: 14px 12px 18px;
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
