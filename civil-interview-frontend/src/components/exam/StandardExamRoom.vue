<template>
  <div class="exam-room" v-if="examStore.currentQuestion">
    <div v-if="!isOnline" class="exam-room__offline-banner">
      网络已断开，请检查网络连接。录音数据会暂存，恢复网络后可继续提交。
    </div>

    <div class="exam-room__header">
      <span class="exam-room__progress">
        {{ examStore.currentQuestionNumber }} / {{ examStore.totalQuestions }}
      </span>
      <span v-if="examStore.fullExamMode" class="exam-room__total-timer">
        {{ formattedElapsed }}
      </span>
      <a-popconfirm title="确定退出考试？已答题目不会丢失。" @confirm="exitExam">
        <a-button type="text" size="small" style="color: rgba(255,255,255,0.8)">
          <CloseOutlined /> 退出
        </a-button>
      </a-popconfirm>
    </div>

    <div class="exam-room__main">
      <div class="exam-room__question">
        <QuestionMetaTags :question="examStore.currentQuestion" emphasis basic-only />
        <div class="question-stem">
          <QuestionRichContent
            :text="examStore.currentQuestion.stem"
            dark
            :show-toggle="false"
          />
        </div>
      </div>
    </div>

    <div
      class="exam-room__camera"
      :class="{
        'is-pip': examStore.status === 'answering' || examStore.status === 'submitting' || examStore.status === 'completed',
        'is-prep': examStore.status === 'preparing' || examStore.status === 'idle'
      }"
      :style="cameraWindowStyle"
      @pointerdown="onCameraPointerDown"
      @contextmenu.prevent
    >
      <VideoPreview
        :stream="stream"
        :recording="examStore.status === 'answering'"
        :duration="recorderDuration"
      />
      <div v-if="examStore.status === 'preparing'" class="camera-hint">
        准备时间，请思考作答思路
      </div>
      <span
        v-for="handle in cameraResizeHandles"
        :key="handle"
        class="camera-resize-handle"
        :class="`is-${handle}`"
        aria-hidden="true"
        @pointerdown.stop="onCameraResizePointerDown($event, handle)"
        @contextmenu.prevent
      />
    </div>

    <div class="exam-room__timer">
      <CountdownTimer
        v-if="examStore.status === 'preparing' || examStore.status === 'answering'"
        :remaining="countdown.remaining.value"
        :total="countdown.total.value"
        :mode="examStore.status === 'preparing' ? 'prep' : 'answer'"
      />
      <div v-else-if="examStore.status === 'submitting'" style="color: rgba(255,255,255,0.7)">
        <a-spin /> <span style="margin-left: 8px">正在评分，请稍候...</span>
      </div>
      <div v-else-if="examStore.status === 'completed'" style="color: #389E0D; font-size: 16px">
        <CheckCircleFilled /> 评分完成
      </div>
    </div>

    <div class="exam-room__waveform" v-show="examStore.status === 'answering'">
      <AudioWaveform
        :stream="stream"
        :active="examStore.status === 'answering'"
        :width="320"
        :height="60"
      />
    </div>

    <div class="exam-room__brief-result" v-if="examStore.status === 'completed' && examStore.scoringResult">
      <div class="brief-score">
        <ScoreRing
          :score="examStore.scoringResult.totalScore"
          :maxScore="examStore.scoringResult.maxScore"
          size="small"
        />
        <span class="brief-score__label">{{ gradeLabel }}</span>
      </div>
    </div>

    <div class="exam-room__controls">
      <RecordingControl
        :status="examStore.status"
        :isLast="examStore.isLastQuestion"
        :submitting-text="examStore.submitStepText"
        :finishing="finishRequested"
        finishing-text="正在分析结果..."
        @start-prep="onStartPrep"
        @start-answer="onStartAnswer"
        @submit="onSubmit"
        @next="onNext"
        @finish="onFinish"
      />
    </div>
  </div>
  <div class="exam-room" style="align-items: center; justify-content: center; color: rgba(255,255,255,0.5);" v-else>
    <p>暂无题目，请返回首页开始测试。</p>
    <a-button type="primary" @click="$router.push('/')">返回首页</a-button>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onUnmounted } from 'vue'
import { useRouter } from 'vue-router'
import { CloseOutlined, CheckCircleFilled } from '@ant-design/icons-vue'
import { useExamStore } from '@/stores/exam'
import { useMediaRecorder } from '@/composables/useMediaRecorder'
import { useCountdown } from '@/composables/useCountdown'
import { useNetworkStatus } from '@/composables/useNetworkStatus'
import { completeExam } from '@/api/exam'
import { EXAM_STATUS, getGrade } from '@/utils/constants'
import VideoPreview from '@/components/recording/VideoPreview.vue'
import AudioWaveform from '@/components/recording/AudioWaveform.vue'
import CountdownTimer from '@/components/common/CountdownTimer.vue'
import RecordingControl from '@/components/recording/RecordingControl.vue'
import ScoreRing from '@/components/common/ScoreRing.vue'
import QuestionMetaTags from '@/components/common/QuestionMetaTags.vue'
import QuestionRichContent from '@/components/common/QuestionRichContent.vue'
import { message } from 'ant-design-vue'
import { logger } from '@/utils/logger'

const CAMERA_DEFAULT = Object.freeze({
  width: 240,
  height: 180,
  margin: 24
})
const CAMERA_MIN = Object.freeze({ width: 180, height: 135 })
const CAMERA_MAX = Object.freeze({ width: 420, height: 315 })
const cameraResizeHandles = Object.freeze(['n', 'e', 's', 'w', 'ne', 'se', 'sw', 'nw'])

const router = useRouter()
const examStore = useExamStore()
const recorder = useMediaRecorder()
const { isOnline } = useNetworkStatus()
const stream = recorder.stream
const recorderDuration = recorder.duration
const countdown = useCountdown(0)

const elapsed = ref(0)
const finishRequested = ref(false)
const cameraWindow = ref({
  width: CAMERA_DEFAULT.width,
  height: CAMERA_DEFAULT.height,
  left: null,
  top: null
})
let elapsedTimer = null
let cameraDragState = null

const cameraWindowStyle = computed(() => ({
  width: `${cameraWindow.value.width}px`,
  height: `${cameraWindow.value.height}px`,
  left: `${cameraWindow.value.left ?? getDefaultCameraPosition().left}px`,
  top: `${cameraWindow.value.top ?? getDefaultCameraPosition().top}px`
}))

const formattedElapsed = computed(() => {
  const m = Math.floor(elapsed.value / 60)
  const s = elapsed.value % 60
  return `${String(m).padStart(2, '0')}:${String(s).padStart(2, '0')}`
})

const gradeLabel = computed(() => {
  if (!examStore.scoringResult) return ''
  return getGrade(examStore.scoringResult.totalScore, examStore.scoringResult.maxScore).label
})

onMounted(async () => {
  resetCameraWindow()
  window.addEventListener('resize', keepCameraWindowInBounds)
  await new Promise((resolve) => setTimeout(resolve, 300))
  const currentStream = await recorder.initStream({ videoEnabled: examStore.videoEnabled })
  if (!currentStream) {
    await new Promise((resolve) => setTimeout(resolve, 500))
    await recorder.initStream({ videoEnabled: examStore.videoEnabled })
  }
  if (examStore.fullExamMode && examStore.examStartTime) {
    elapsedTimer = setInterval(() => {
      elapsed.value = Math.floor((Date.now() - examStore.examStartTime) / 1000)
    }, 1000)
  }
  if (examStore.currentQuestion && examStore.status === EXAM_STATUS.IDLE && examStore.fullExamMode) {
    onStartPrep()
  }
})

onUnmounted(() => {
  window.removeEventListener('resize', keepCameraWindowInBounds)
  stopCameraInteraction()
  recorder.destroyStream()
  countdown.stop()
  clearInterval(elapsedTimer)
  if (examStore.fullExamMode) {
    examStore.examElapsed = elapsed.value
  }
})

function onStartPrep() {
  const q = examStore.currentQuestion
  examStore.startPreparing()
  countdown.reset(q.prepTime || 90)
  countdown.onFinish(() => {
    onStartAnswer()
  })
  countdown.start()
}

function onStartAnswer() {
  countdown.stop()
  examStore.startAnswering()
  recorder.startRecording()
  const q = examStore.currentQuestion
  countdown.reset(q.answerTime || 180)
  countdown.onFinish(() => {
    onSubmit()
  })
  countdown.start()
}

async function onSubmit() {
  if (finishRequested.value) return
  countdown.stop()
  try {
    const blob = await recorder.stopRecording()
    await examStore.submitAnswer(blob)
    if (!examStore.isLastQuestion) {
      message.success('本题已提交，后台评分中。')
      onNext()
    }
  } catch (error) {
    message.error(`提交失败: ${error.message || '未知错误'}`)
  }
}

function onNext() {
  examStore.nextQuestion()
  countdown.reset(0)
  if (examStore.fullExamMode) {
    setTimeout(() => onStartPrep(), 500)
  }
}

async function onFinish() {
  if (finishRequested.value) return
  const examId = examStore.examId
  if (!examId) {
    message.error('考试数据异常，返回首页')
    router.push('/')
    return
  }
  finishRequested.value = true
  try {
    await examStore.evaluatePendingAnswers()
    await completeExam(examId)
  } catch (error) {
    logger.error('Exam history save failed', {
      event: 'exam.history.save_failed',
      exam_id: examId,
      error
    })
  }
  countdown.stop()
  recorder.destroyStream()
  examStore.exitExam()
  router.push(`/result/${examId}`)
}

async function exitExam() {
  countdown.stop()
  recorder.destroyStream()
  const examId = examStore.examId
  if (examId && examStore.answers.length > 0) {
    try {
      await examStore.waitForPendingProcessing()
      await completeExam(examId)
      message.success('练习记录已保存')
    } catch (error) {
      logger.error('Exam progress save failed', {
        event: 'exam.progress.save_failed',
        exam_id: examId,
        error
      })
    }
  }
  examStore.exitExam()
  router.push('/')
}

function getViewportSize() {
  return {
    width: window.innerWidth || document.documentElement.clientWidth || 1024,
    height: window.innerHeight || document.documentElement.clientHeight || 768
  }
}

function getDefaultCameraPosition(width = cameraWindow.value.width, height = cameraWindow.value.height) {
  const viewport = getViewportSize()
  return {
    left: Math.max(CAMERA_DEFAULT.margin, viewport.width - width - CAMERA_DEFAULT.margin),
    top: Math.max(CAMERA_DEFAULT.margin, viewport.height - height - CAMERA_DEFAULT.margin)
  }
}

function clampCameraWindow(next) {
  const viewport = getViewportSize()
  const sizeLimits = getCameraSizeLimits()
  const width = Math.min(Math.max(next.width, sizeLimits.minWidth), sizeLimits.maxWidth)
  const height = Math.min(Math.max(next.height, sizeLimits.minHeight), sizeLimits.maxHeight)
  return {
    width,
    height,
    left: Math.min(Math.max(next.left, CAMERA_DEFAULT.margin), Math.max(CAMERA_DEFAULT.margin, viewport.width - width - CAMERA_DEFAULT.margin)),
    top: Math.min(Math.max(next.top, CAMERA_DEFAULT.margin), Math.max(CAMERA_DEFAULT.margin, viewport.height - height - CAMERA_DEFAULT.margin))
  }
}

function resetCameraWindow() {
  const position = getDefaultCameraPosition(CAMERA_DEFAULT.width, CAMERA_DEFAULT.height)
  cameraWindow.value = clampCameraWindow({
    ...position,
    width: CAMERA_DEFAULT.width,
    height: CAMERA_DEFAULT.height
  })
}

function keepCameraWindowInBounds() {
  cameraWindow.value = clampCameraWindow(cameraWindow.value)
}

function onCameraPointerDown(event) {
  if (event.button !== 0) return
  const rect = event.currentTarget.getBoundingClientRect()
  startCameraInteraction(event, {
    mode: 'move',
    rect
  })
}

function onCameraResizePointerDown(event, handle) {
  if (event.button !== 0) return
  const rect = event.currentTarget.parentElement.getBoundingClientRect()
  startCameraInteraction(event, {
    mode: 'resize',
    rect,
    handle
  })
}

function startCameraInteraction(event, { mode, rect, handle = '' }) {
  cameraDragState = {
    mode,
    handle,
    startX: event.clientX,
    startY: event.clientY,
    startLeft: rect.left,
    startTop: rect.top,
    startWidth: rect.width,
    startHeight: rect.height
  }

  event.currentTarget.setPointerCapture?.(event.pointerId)
  window.addEventListener('pointermove', onCameraPointerMove)
  window.addEventListener('pointerup', stopCameraInteraction)
  event.preventDefault()
}

function onCameraPointerMove(event) {
  if (!cameraDragState) return
  const deltaX = event.clientX - cameraDragState.startX
  const deltaY = event.clientY - cameraDragState.startY

  if (cameraDragState.mode === 'resize') {
    const movesLeft = cameraDragState.handle.includes('w')
    const movesRight = cameraDragState.handle.includes('e')
    const movesTop = cameraDragState.handle.includes('n')
    const movesBottom = cameraDragState.handle.includes('s')
    const sizeLimits = getCameraSizeLimits()
    let nextLeft = movesLeft ? cameraDragState.startLeft + deltaX : cameraDragState.startLeft
    let nextTop = movesTop ? cameraDragState.startTop + deltaY : cameraDragState.startTop
    let nextWidth = cameraDragState.startWidth
      + (movesRight ? deltaX : 0)
      - (movesLeft ? deltaX : 0)
    let nextHeight = cameraDragState.startHeight
      + (movesBottom ? deltaY : 0)
      - (movesTop ? deltaY : 0)

    if (movesLeft) {
      nextWidth = Math.min(Math.max(nextWidth, sizeLimits.minWidth), sizeLimits.maxWidth)
      nextLeft = cameraDragState.startLeft + cameraDragState.startWidth - nextWidth
    }
    if (movesTop) {
      nextHeight = Math.min(Math.max(nextHeight, sizeLimits.minHeight), sizeLimits.maxHeight)
      nextTop = cameraDragState.startTop + cameraDragState.startHeight - nextHeight
    }

    cameraWindow.value = clampCameraWindow({
      left: nextLeft,
      top: nextTop,
      width: nextWidth,
      height: nextHeight
    })
    return
  }

  cameraWindow.value = clampCameraWindow({
    left: cameraDragState.startLeft + deltaX,
    top: cameraDragState.startTop + deltaY,
    width: cameraDragState.startWidth,
    height: cameraDragState.startHeight
  })
}

function getCameraSizeLimits() {
  const viewport = getViewportSize()
  return {
    minWidth: CAMERA_MIN.width,
    minHeight: CAMERA_MIN.height,
    maxWidth: Math.min(CAMERA_MAX.width, viewport.width - CAMERA_DEFAULT.margin * 2),
    maxHeight: Math.min(CAMERA_MAX.height, viewport.height - CAMERA_DEFAULT.margin * 2)
  }
}

function stopCameraInteraction() {
  cameraDragState = null
  window.removeEventListener('pointermove', onCameraPointerMove)
  window.removeEventListener('pointerup', stopCameraInteraction)
}
</script>

<style lang="less" scoped>
@import '@/styles/exam-room.less';

.question-stem {
  margin-top: 10px;
}

.question-stem :deep(.question-rich-content__body) {
  color: rgba(255, 255, 255, 0.9);
}

.brief-score {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 12px;
  padding: 8px 16px;
}

.brief-score__label {
  font-size: 18px;
  font-weight: 600;
  color: #fff;
}

.exam-room__brief-result {
  flex-shrink: 0;
}

.exam-room__total-timer {
  background: rgba(255, 255, 255, 0.15);
  padding: 2px 10px;
  border-radius: 12px;
  font-size: 13px;
  color: rgba(255, 255, 255, 0.85);
  font-variant-numeric: tabular-nums;
}

.exam-room__offline-banner {
  background: #fff1f0;
  color: #cf1322;
  text-align: center;
  padding: 8px 16px;
  font-size: 13px;
  font-weight: 500;
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  z-index: 1000;
  animation: slideDown 0.3s ease;
}

@keyframes slideDown {
  from { transform: translateY(-100%); }
  to { transform: translateY(0); }
}
</style>
