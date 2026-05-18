<template>
  <view class="exam-room">
    <view v-if="question" class="exam-room__body">
      <view class="question-book" :class="{ 'question-book--long': questionBookLong }">
        <view class="question-book__head">
          <text class="question-book__title">题本区</text>
          <text class="question-book__meta">第 {{ questionBookIndex + 1 }} / {{ examStore.totalQuestions }} 题</text>
        </view>
        <swiper
          class="question-book__swiper"
          :current="questionBookIndex"
          :indicator-dots="examStore.totalQuestions > 1"
          indicator-color="rgba(27,95,170,0.22)"
          indicator-active-color="#1b5faa"
          @change="onQuestionBookChange"
        >
          <swiper-item
            v-for="(item, index) in examStore.questions"
            :key="item.id || index"
          >
            <view
              class="question-book__card"
              :class="{ 'question-book__card--current': index === examStore.currentIndex }"
            >
              <view class="question-tags">
                <text class="question-tag">{{ provinceLabel(item) }}</text>
                <text class="question-tag question-tag--blue">{{ categoryLabel(item) }}</text>
                <text v-if="index === examStore.currentIndex" class="question-tag question-tag--active">当前作答</text>
              </view>
              <scroll-view scroll-y class="question-book__stem-scroll">
                <text class="question-book__stem">{{ item.stem }}</text>
              </scroll-view>
            </view>
          </swiper-item>
        </swiper>
      </view>

      <view
        v-if="useVideoMode"
        class="floating-camera"
        :class="cameraSizeClass"
        @tap="handleCameraTap"
      >
        <camera
          class="floating-camera__camera"
          device-position="front"
          flash="off"
          mode="normal"
          resolution="medium"
          frame-size="medium"
          @error="onCameraError"
        />
        <view class="floating-camera__mask">
          <text class="floating-camera__status">{{ floatingCameraStatus }}</text>
          <text class="floating-camera__size">{{ cameraSizeText }}</text>
        </view>
      </view>

      <scroll-view scroll-y class="exam-room__scroll" :style="{ paddingTop: questionBookScrollPadding }">
        <view class="mock-scene">
          <image
            class="mock-scene__image"
            src="/static/exam/mock-interview-room-live-current.jpg"
            mode="aspectFill"
          />
          <view class="mock-scene__timer">
            <text class="mock-scene__timer-label">{{ sceneTimerLabel }}</text>
            <text class="mock-scene__timer-value">{{ formatTime(sceneTimeLeft) }}</text>
          </view>
        </view>

        <view class="question-panel">
        <view v-if="isJiangsuReading" class="card reading-list-card">
          <text class="reading-list__title">江苏 5+15 阅读题本</text>
          <text v-for="(item, index) in examStore.questions" :key="item.id || index" class="reading-list__item">
            {{ index + 1 }}. {{ item.stem }}
          </text>
        </view>

        <view class="card">
          <view class="section-head">
            <text class="section-title">作答区</text>
            <text class="muted">{{ useVideoMode ? '录像 + 录音' : '仅录音' }}</text>
          </view>

          <view class="record-panel">
            <view class="record-panel__status">
              <text>{{ captureStatusText }}</text>
              <text v-if="captureReady" class="record-panel__ready">已记录</text>
            </view>
            <view v-if="useVideoMode" class="record-panel__camera-status">
              {{ cameraStatusText }}
            </view>
            <view class="record-actions">
              <button
                class="secondary-button"
                :disabled="captureActive || examStore.loading"
                @tap="startCapture"
              >
                {{ useVideoMode ? '开始录像+录音' : '开始录音' }}
              </button>
              <button
                class="secondary-button"
                :disabled="!captureActive || examStore.loading"
                @tap="stopCapture"
              >
                {{ useVideoMode ? '停止录像+录音' : '停止录音' }}
              </button>
            </view>
          </view>
        </view>
        </view>
      </scroll-view>

      <view class="room-actions">
        <button class="secondary-button" @tap="goBackHome">退出</button>
        <button class="primary-button" :loading="examStore.loading" @tap="submitAnswer">
          {{ examStore.isLastQuestion ? '提交并看结果' : '提交本题' }}
        </button>
      </view>
    </view>
    <view v-else class="exam-room__empty">
      <EmptyState title="考场未创建" desc="请先从模考准备页进入。" />
      <button class="primary-button" @tap="goPrepare">去准备</button>
    </view>
  </view>
</template>

<script setup>
import { computed, nextTick, onBeforeUnmount, ref, watch } from 'vue'
import { onHide, onLoad, onReady } from '@dcloudio/uni-app'
import EmptyState from '../../components/EmptyState.vue'
import { completeTrial } from '../../api/trial'
import { reportUsage } from '../../api/usage'
import { useExamStore } from '../../stores/exam'
import { useSubscriptionStore } from '../../stores/subscription'
import { useUserStore } from '../../stores/user'
import { formatTime } from '../../utils/format'
import { getCategoryName, getProvinceName } from '../../utils/constants'
import { hideLoading, showLoading, toast } from '../../utils/navigation'

const examStore = useExamStore()
const subscriptionStore = useSubscriptionStore()
const userStore = useUserStore()
const phase = ref('preparing')
const prepLeft = ref(userStore.preferences.defaultPrepTime)
const answerLeft = ref(userStore.preferences.defaultAnswerTime)
const recording = ref(false)
const recordedFile = ref('')
const recorder = ref(null)
const videoRecording = ref(false)
const recordedVideoFile = ref('')
const cameraContext = ref(null)
const cameraError = ref('')
const cameraAvailable = ref(false)
const cameraSize = ref('small')
const selectedMediaType = ref('')
const questionStartedAt = ref(Date.now())
const questionBookIndex = ref(0)
const reportedQuestionKeys = new Set()
const JIANGSU_MOCK_TIMING_MODE = 'jiangsu_5_15'
const JIANGSU_READING_SECONDS = 5 * 60
const JIANGSU_ANSWER_SECONDS = 15 * 60
let timer = null
let pendingRecordStopResolve = null
let lastCameraTapAt = 0

const question = computed(() => examStore.currentQuestion)
const useVideoMode = computed(() => examStore.mediaMode === 'video')
const questionBookLong = computed(() => {
  const item = examStore.questions[questionBookIndex.value] || question.value || {}
  return String(item?.stem || '').length > 86
})
const questionBookScrollPadding = computed(() => (
  questionBookLong.value
    ? 'calc(430rpx + env(safe-area-inset-top))'
    : 'calc(338rpx + env(safe-area-inset-top))'
))
const isMockLikeSource = computed(() => examStore.source === 'mock')
const isJiangsuMockTiming = computed(() => isMockLikeSource.value && examStore.questions.some((item) => (
  item?.mockTimingMode === JIANGSU_MOCK_TIMING_MODE
)))
const isJiangsuReading = computed(() => isJiangsuMockTiming.value && phase.value === 'reading')
const activeTimerLabel = computed(() => {
  if (phase.value === 'reading') return '阅读'
  return phase.value === 'preparing' ? '准备' : '作答'
})
const sceneTimeLeft = computed(() => {
  if (phase.value === 'preparing' || phase.value === 'reading') {
    return Math.max(0, Number(prepLeft.value) || 0) + Math.max(0, Number(answerLeft.value) || 0)
  }
  return Math.max(0, Number(answerLeft.value) || 0)
})
const sceneTimerLabel = computed(() => (
  isJiangsuMockTiming.value || isMockLikeSource.value ? '总倒计时' : activeTimerLabel.value
))
const cameraStatusText = computed(() => {
  if (!useVideoMode.value) return '已选择仅录音，不启用摄像头'
  if (cameraError.value) return cameraError.value
  if (videoRecording.value) return '摄像头录像中，请保持正对镜头'
  if (recordedVideoFile.value) return '录像已保存，可提交或重新录制'
  if (!cameraAvailable.value) return '当前环境暂不支持录像，请切换仅录音后继续'
  return '请授权摄像头，可使用录像提交作答'
})
const recordStatusText = computed(() => {
  if (recording.value) return '录音中，请保持语速稳定'
  if (recordedFile.value) return '录音已保存，可提交或重新录制'
  return '请授权麦克风，可使用录音提交作答'
})
const captureActive = computed(() => (
  useVideoMode.value ? (recording.value || videoRecording.value) : recording.value
))
const captureReady = computed(() => (
  useVideoMode.value ? Boolean(recordedVideoFile.value || recordedFile.value) : Boolean(recordedFile.value)
))
const captureStatusText = computed(() => {
  if (!useVideoMode.value) return recordStatusText.value
  if (recording.value && videoRecording.value) return '录像与录音同步记录中'
  if (videoRecording.value) return '录像中，音频将随视频一并保存'
  if (recording.value) return '录音中，正在等待摄像头录像'
  if (recordedVideoFile.value) return '录像已保存，可提交或重新录制'
  if (recordedFile.value) return '已保存录音，未获得录像文件'
  return '请授权摄像头和麦克风，开始后同步记录'
})
const cameraSizeClass = computed(() => `floating-camera--${cameraSize.value}`)
const cameraSizeText = computed(() => {
  const labels = { small: '小窗', medium: '中窗', large: '大窗' }
  return `${labels[cameraSize.value] || '小窗'} · 双击切换`
})
const floatingCameraStatus = computed(() => {
  if (videoRecording.value) return '录像中'
  if (cameraError.value) return '摄像头异常'
  if (recordedVideoFile.value) return '已保存'
  return '摄像头'
})
const currentMedia = computed(() => {
  if (!useVideoMode.value && recordedFile.value) {
    return { filePath: recordedFile.value, mediaType: 'audio' }
  }
  if (selectedMediaType.value === 'video' && recordedVideoFile.value) {
    return { filePath: recordedVideoFile.value, mediaType: 'video' }
  }
  if (selectedMediaType.value === 'audio' && recordedFile.value) {
    return { filePath: recordedFile.value, mediaType: 'audio' }
  }
  if (recordedVideoFile.value) return { filePath: recordedVideoFile.value, mediaType: 'video' }
  if (recordedFile.value) return { filePath: recordedFile.value, mediaType: 'audio' }
  return { filePath: '', mediaType: '' }
})

onLoad(() => {
  setupRecorder()
  resetQuestionState()
  startTimer()
})

onReady(() => {
  if (useVideoMode.value) {
    setupCamera()
  }
})

onHide(() => {
  stopActiveCapture({ silent: true })
})

onBeforeUnmount(() => {
  clearInterval(timer)
  stopActiveCapture({ silent: true })
})

watch(() => examStore.currentIndex, (index) => {
  questionBookIndex.value = Math.max(0, Number(index) || 0)
})

watch(useVideoMode, async (enabled) => {
  if (enabled) {
    await nextTick()
    setupCamera()
    return
  }
  cameraError.value = ''
  recordedVideoFile.value = ''
  if (selectedMediaType.value === 'video') selectedMediaType.value = recordedFile.value ? 'audio' : ''
})

function provinceLabel(item = {}) {
  return getProvinceName(item?.province || 'national')
}

function categoryLabel(item = {}) {
  return getCategoryName(item?.dimension || item?.type || '')
}

function onQuestionBookChange(event) {
  const current = Number(event?.detail?.current ?? 0)
  questionBookIndex.value = Math.max(0, Math.min(current, Math.max(examStore.totalQuestions - 1, 0)))
}

function setupRecorder() {
  if (typeof uni.getRecorderManager !== 'function') return
  recorder.value = uni.getRecorderManager()
  recorder.value.onStop((res) => {
    recording.value = false
    recordedFile.value = res.tempFilePath || ''
    if (recordedFile.value && (!useVideoMode.value || !recordedVideoFile.value)) {
      selectedMediaType.value = 'audio'
    }
    if (pendingRecordStopResolve) {
      pendingRecordStopResolve(recordedFile.value)
      pendingRecordStopResolve = null
    }
  })
  recorder.value.onError((error) => {
    recording.value = false
    if (pendingRecordStopResolve) {
      pendingRecordStopResolve('')
      pendingRecordStopResolve = null
    }
    toast(error?.errMsg || '录音失败')
  })
}

function setupCamera() {
  if (!useVideoMode.value) return
  if (typeof uni.createCameraContext !== 'function') {
    cameraAvailable.value = false
    cameraError.value = '当前环境不支持摄像头录像'
    return
  }
  cameraContext.value = uni.createCameraContext()
  cameraAvailable.value = true
}

function startTimer() {
  clearInterval(timer)
  timer = setInterval(() => {
    if (phase.value === 'preparing' || phase.value === 'reading') {
      prepLeft.value -= 1
      if (prepLeft.value <= 0) phase.value = 'answering'
      return
    }
    answerLeft.value = Math.max(0, answerLeft.value - 1)
  }, 1000)
}

function resetQuestionState() {
  phase.value = isJiangsuMockTiming.value ? 'reading' : 'preparing'
  prepLeft.value = isJiangsuMockTiming.value
    ? JIANGSU_READING_SECONDS
    : Number(question.value?.prepTime || userStore.preferences.defaultPrepTime || 90)
  answerLeft.value = isJiangsuMockTiming.value
    ? JIANGSU_ANSWER_SECONDS
    : Number(question.value?.answerTime || userStore.preferences.defaultAnswerTime || 180)
  questionStartedAt.value = Date.now()
  questionBookIndex.value = Math.max(0, examStore.currentIndex)
  resetAnswerInputState()
}

function resetAnswerInputState() {
  recording.value = false
  recordedFile.value = ''
  videoRecording.value = false
  recordedVideoFile.value = ''
  selectedMediaType.value = ''
}

function currentUsageSeconds() {
  const elapsed = Math.ceil((Date.now() - questionStartedAt.value) / 1000)
  const maxSeconds = isJiangsuMockTiming.value
    ? JIANGSU_READING_SECONDS + JIANGSU_ANSWER_SECONDS
    : Number(question.value?.prepTime || userStore.preferences.defaultPrepTime || 90)
      + Number(question.value?.answerTime || userStore.preferences.defaultAnswerTime || 180)
  return Math.max(1, Math.min(elapsed, maxSeconds || elapsed))
}

function canRecordNow() {
  if (isJiangsuReading.value) {
    toast('当前是 5 分钟阅读阶段，请阅读结束后再开始作答')
    return false
  }
  return true
}

function usageType() {
  if (examStore.source === 'trial') return 'trial'
  if (isMockLikeSource.value) return 'mock'
  return 'practice'
}

async function syncUsageAndTrial(answer) {
  const key = `${answer.examId}:${answer.questionId}:${answer.questionIndex}`
  if (!reportedQuestionKeys.has(key)) {
    reportedQuestionKeys.add(key)
    await reportUsage({
      examId: answer.examId,
      questionId: answer.questionId,
      usageSeconds: currentUsageSeconds(),
      usageType: usageType()
    }).then(() => subscriptionStore.refresh({ skipErrorHandler: true })).catch(() => null)
  }

  if (examStore.source === 'trial' && examStore.isLastQuestion) {
    await completeTrial().then(() => subscriptionStore.refresh({ skipErrorHandler: true })).catch(() => null)
  }
}

function startRecorderInternal() {
  if (!recorder.value) {
    toast('当前环境不支持录音')
    return false
  }
  if (recording.value) {
    return true
  }
  phase.value = 'answering'
  recordedFile.value = ''
  try {
    recorder.value.start({
      duration: 300000,
      sampleRate: 16000,
      numberOfChannels: 1,
      encodeBitRate: 48000,
      format: 'mp3'
    })
    recording.value = true
    return true
  } catch {
    toast('无法启动录音')
    return false
  }
}

function startRecord() {
  if (useVideoMode.value) {
    startVideoWithAudio()
    return
  }
  if (!canRecordNow()) return
  startRecorderInternal()
}

function stopRecord() {
  if (!recorder.value || !recording.value) return
  recorder.value.stop()
}

function stopRecordAsync() {
  if (!recorder.value || !recording.value) return Promise.resolve('')
  return new Promise((resolve) => {
    pendingRecordStopResolve = resolve
    try {
      recorder.value.stop()
    } catch {
      recording.value = false
      pendingRecordStopResolve = null
      resolve('')
    }
  })
}

function handleVideoSaved(res, message = '录像已保存') {
  videoRecording.value = false
  const videoPath = res?.tempVideoPath || ''
  if (!videoPath) {
    toast('录像未保存，请重新录制')
    return
  }
  recordedVideoFile.value = videoPath
  selectedMediaType.value = 'video'
  toast(message, 'success')
}

function startVideoRecord() {
  if (!canRecordNow()) return
  if (!useVideoMode.value) {
    toast('当前已选择仅录音')
    return
  }
  if (!cameraContext.value) {
    setupCamera()
  }
  if (!cameraContext.value) {
    toast(cameraError.value || '当前环境不支持摄像头')
    return
  }
  phase.value = 'answering'
  cameraError.value = ''
  recordedVideoFile.value = ''
  try {
    cameraContext.value.startRecord({
      timeout: Math.min(300, Math.max(30, Number(answerLeft.value) || 180)),
      timeoutCallback(res) {
        handleVideoSaved(res, '录像已自动保存')
      },
      success() {
        videoRecording.value = true
        cameraAvailable.value = true
        selectedMediaType.value = 'video'
      },
      fail(error) {
        videoRecording.value = false
        cameraAvailable.value = false
        const message = error?.errMsg || '无法启动摄像头录像'
        cameraError.value = message
        if (recording.value) stopRecordAsync()
        toast(message)
      }
    })
  } catch (error) {
    videoRecording.value = false
    cameraAvailable.value = false
    const message = error?.message || '无法启动摄像头录像'
    cameraError.value = message
    if (recording.value) stopRecordAsync()
    toast(message)
  }
}

function stopVideoRecord(options = {}) {
  const silent = options.silent === true
  if (!cameraContext.value || !videoRecording.value) return Promise.resolve('')
  return new Promise((resolve) => {
    try {
      cameraContext.value.stopRecord({
        compressed: true,
        success(res) {
          videoRecording.value = false
          recordedVideoFile.value = res?.tempVideoPath || ''
          if (recordedVideoFile.value) selectedMediaType.value = 'video'
          if (silent) {
            resolve(recordedVideoFile.value)
          } else {
            handleVideoSaved(res, '录像已保存')
            resolve(recordedVideoFile.value)
          }
        },
        fail(error) {
          videoRecording.value = false
          if (!silent) toast(error?.errMsg || '录像停止失败')
          resolve('')
        }
      })
    } catch (error) {
      videoRecording.value = false
      if (!silent) toast(error?.message || '录像停止失败')
      resolve('')
    }
  })
}

function onCameraError(error) {
  cameraError.value = error?.detail?.errMsg || error?.errMsg || '摄像头不可用，请检查授权'
  cameraAvailable.value = false
}

function startVideoWithAudio() {
  if (!canRecordNow()) return
  if (!useVideoMode.value) {
    startRecord()
    return
  }
  if (recording.value || videoRecording.value) {
    toast('当前正在记录作答')
    return
  }
  recordedFile.value = ''
  recordedVideoFile.value = ''
  selectedMediaType.value = ''

  if (!startRecorderInternal()) return
  startVideoRecord()
}

async function stopVideoWithAudio() {
  const videoPath = videoRecording.value ? await stopVideoRecord() : recordedVideoFile.value
  const audioPath = recording.value ? await stopRecordAsync() : recordedFile.value
  if (videoPath || recordedVideoFile.value) {
    selectedMediaType.value = 'video'
  } else if (audioPath || recordedFile.value) {
    selectedMediaType.value = 'audio'
  }
}

function stopActiveCapture(options = {}) {
  if (videoRecording.value) stopVideoRecord({ silent: options.silent === true })
  if (recording.value) stopRecord()
}

function startCapture() {
  if (useVideoMode.value) {
    startVideoWithAudio()
    return
  }
  startRecord()
}

function stopCapture() {
  if (useVideoMode.value) {
    stopVideoWithAudio()
    return
  }
  stopRecord()
}

function cycleCameraSize() {
  const order = ['small', 'medium', 'large']
  const currentIndex = order.indexOf(cameraSize.value)
  cameraSize.value = order[(currentIndex + 1) % order.length] || 'small'
}

function handleCameraTap() {
  const now = Date.now()
  if (now - lastCameraTapAt < 320) {
    cycleCameraSize()
    lastCameraTapAt = 0
    return
  }
  lastCameraTapAt = now
}

async function submitAnswer() {
  if (isJiangsuReading.value) {
    toast('阅读阶段暂不能提交，请阅读结束后作答')
    return
  }
  if (recording.value) {
    await stopRecordAsync()
  }
  if (videoRecording.value) {
    await stopVideoRecord()
  }
  const media = currentMedia.value

  showLoading(examStore.isLastQuestion ? '生成结果' : '保存作答')
  try {
    const answer = await examStore.submitCurrentAnswer({
      filePath: media.filePath,
      mediaType: media.mediaType || 'audio',
      audioFilePath: recordedFile.value || ''
    })
    await syncUsageAndTrial(answer)

    if (examStore.isLastQuestion) {
      const finishedExamId = examStore.examId
      await examStore.finish()
      examStore.reset()
      uni.redirectTo({
        url: `/pages/result/index?examId=${encodeURIComponent(finishedExamId)}&questionId=${encodeURIComponent(answer.questionId)}`
      })
      return
    }

    toast('本题已提交，后台评分中', 'success')
    if (examStore.goNext()) {
      if (isJiangsuMockTiming.value) {
        resetAnswerInputState()
        questionStartedAt.value = Date.now()
      } else {
        resetQuestionState()
      }
    }
  } catch (error) {
    toast(error?.message || '评分失败')
  } finally {
    hideLoading()
  }
}

function goPrepare() {
  uni.redirectTo({ url: '/pages/exam/prepare' })
}

function goBackHome() {
  uni.showModal({
    title: '退出考场',
    content: '当前作答进度可能不会保存，确认退出吗？',
    success(res) {
      if (res.confirm) {
        stopActiveCapture({ silent: true })
        examStore.reset()
        uni.switchTab({ url: '/pages/home/index' })
      }
    }
  })
}
</script>

<style scoped>
.exam-room {
  min-height: 100vh;
  background: #2b1b13;
}

.exam-room__body {
  display: flex;
  flex-direction: column;
  height: 100vh;
}

.exam-room__scroll {
  flex: 1;
  min-height: 0;
  background:
    linear-gradient(180deg, rgba(56, 34, 23, 0.96) 0%, rgba(38, 24, 18, 0.98) 42%, #f0e7d8 42%, #f5efe4 100%);
}

.mock-scene {
  position: relative;
  height: 330rpx;
  overflow: hidden;
  background: #2b1b13;
}

.mock-scene__image {
  position: absolute;
  inset: 0;
  width: 100%;
  height: 100%;
}

.mock-scene__timer {
  position: absolute;
  top: 116rpx;
  right: 18rpx;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  width: 86rpx;
  height: 42rpx;
  border: 1rpx solid rgba(255, 42, 42, 0.38);
  background: #170c0a;
  box-shadow: 0 0 12rpx rgba(255, 24, 24, 0.28);
}

.mock-scene__timer-label,
.mock-scene__timer-value {
  display: block;
  line-height: 1;
}

.mock-scene__timer-label {
  margin-bottom: 3rpx;
  color: rgba(255, 118, 118, 0.76);
  font-size: 13rpx;
  font-weight: 700;
}

.mock-scene__timer-value {
  color: #ff3030;
  font-size: 21rpx;
  font-weight: 900;
  font-family: DIN Alternate, Arial, sans-serif;
}

.question-book {
  position: fixed;
  top: calc(18rpx + env(safe-area-inset-top));
  right: 24rpx;
  left: 24rpx;
  z-index: 30;
  padding: 18rpx;
  border: 1rpx solid rgba(128, 83, 52, 0.18);
  border-radius: 18rpx;
  background: rgba(255, 250, 241, 0.97);
  box-shadow: 0 18rpx 42rpx rgba(36, 19, 10, 0.24);
}

.question-book--long .question-book__swiper {
  height: 322rpx;
}

.question-book--long .question-book__card {
  height: 286rpx;
}

.question-book--long .question-book__stem-scroll {
  max-height: 212rpx;
}

.question-book__head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 12rpx;
}

.question-book__title {
  color: #1f2b3d;
  font-size: 27rpx;
  font-weight: 900;
}

.question-book__meta {
  color: #6f7c8f;
  font-size: 23rpx;
  font-weight: 700;
}

.question-book__swiper {
  height: 230rpx;
}

.question-book__card {
  height: 194rpx;
  padding: 18rpx;
  border: 1rpx solid rgba(128, 83, 52, 0.16);
  border-radius: 14rpx;
  background: linear-gradient(180deg, #fffdf8 0%, #f5ead9 100%);
}

.question-book__card--current {
  border-color: #9d6539;
}

.question-book__stem-scroll {
  max-height: 132rpx;
  overflow: hidden;
}

.question-book__stem {
  display: block;
  color: #1f2b3d;
  font-size: 28rpx;
  font-weight: 700;
  line-height: 1.55;
}

.question-tag--active {
  background: #e6f7ff;
  color: #0958a5;
}

.question-panel {
  padding: 24rpx 28rpx;
  background: #f5efe4;
}

.question-panel :deep(.card),
.question-panel .card {
  border-color: rgba(128, 83, 52, 0.16);
  background: rgba(255, 252, 246, 0.98);
}

.question-tags {
  display: flex;
  flex-wrap: wrap;
  gap: 10rpx;
  margin-bottom: 16rpx;
}

.question-tag {
  padding: 6rpx 14rpx;
  border-radius: 999rpx;
  background: #fff2e8;
  color: #8a4d17;
  font-size: 22rpx;
  font-weight: 700;
}

.question-tag--blue {
  background: #e8f4fd;
  color: #1b5faa;
}

.question-tag--score {
  background: #fff6d8;
  color: #8a5a00;
}

.reading-list {
  margin-top: 22rpx;
  padding-top: 18rpx;
  border-top: 1rpx solid #eef2f6;
}

.reading-list__title,
.reading-list__item {
  display: block;
}

.reading-list__title {
  color: #1b5faa;
  font-size: 25rpx;
  font-weight: 800;
}

.reading-list__item {
  margin-top: 8rpx;
  color: #6f7c8f;
  font-size: 24rpx;
  line-height: 1.5;
}

.record-panel {
  margin-top: 22rpx;
  padding-top: 22rpx;
  border-top: 1rpx solid #eef2f6;
}

.record-panel__status {
  display: flex;
  justify-content: space-between;
  color: #6f7c8f;
  font-size: 24rpx;
}

.record-panel__ready {
  color: #389e0d;
  font-weight: 700;
}

.record-panel__camera-status {
  margin-top: 12rpx;
  padding: 14rpx 16rpx;
  border-radius: 12rpx;
  background: #fff7e8;
  color: #7a4520;
  font-size: 23rpx;
  line-height: 1.5;
}

.record-actions {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 16rpx;
  margin-top: 18rpx;
}

.room-actions {
  display: grid;
  grid-template-columns: 180rpx minmax(0, 1fr);
  gap: 16rpx;
  padding: 18rpx 28rpx calc(18rpx + env(safe-area-inset-bottom));
  border-top: 1rpx solid rgba(128, 83, 52, 0.16);
  background: #fffaf1;
}

.exam-room__empty {
  padding: 30rpx;
}

.floating-camera {
  position: fixed;
  right: 24rpx;
  bottom: calc(142rpx + env(safe-area-inset-bottom));
  z-index: 42;
  overflow: hidden;
  border: 4rpx solid rgba(255, 241, 218, 0.92);
  border-radius: 18rpx;
  background: #080808;
  box-shadow: 0 16rpx 38rpx rgba(22, 12, 7, 0.38);
}

.floating-camera--small {
  width: 148rpx;
  height: 198rpx;
}

.floating-camera--medium {
  width: 212rpx;
  height: 284rpx;
}

.floating-camera--large {
  width: 284rpx;
  height: 378rpx;
}

.floating-camera__camera {
  width: 100%;
  height: 100%;
}

.floating-camera__mask {
  position: absolute;
  right: 0;
  bottom: 0;
  left: 0;
  padding: 8rpx 10rpx;
  background: linear-gradient(180deg, transparent 0%, rgba(0, 0, 0, 0.72) 38%, rgba(0, 0, 0, 0.86) 100%);
}

.floating-camera__status,
.floating-camera__size {
  display: block;
  color: #fff7e8;
  font-size: 19rpx;
  font-weight: 800;
  line-height: 1.25;
}

.floating-camera__size {
  margin-top: 2rpx;
  color: rgba(255, 247, 232, 0.68);
  font-size: 17rpx;
  font-weight: 600;
}
</style>
