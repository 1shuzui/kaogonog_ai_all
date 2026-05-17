<template>
  <view class="exam-room">
    <view v-if="question" class="exam-room__body">
      <button class="exam-room__exit-fixed" @tap="goBackHome">退出</button>

      <view class="mock-scene">
        <image
          class="mock-scene__image"
          src="/static/exam/mock-interview-room-live-current.png"
          mode="aspectFill"
        />
        <view class="mock-scene__shade"></view>

        <view class="room-header room-header--floating">
          <view>
            <text class="room-header__count">当前作答第 {{ examStore.questionNumber }} / {{ examStore.totalQuestions }} 题</text>
            <text class="room-header__sub">{{ provinceName }} · {{ categoryName }}</text>
          </view>
          <text class="room-header__timer">{{ activeTimerLabel }} {{ formatTime(activeTimeLeft) }}</text>
        </view>

        <view class="examiner-panel">
          <text class="examiner-panel__kicker">AI 模拟考场</text>
          <text class="examiner-panel__title">公务员结构化面试模拟现场</text>
          <text class="examiner-panel__desc">{{ examinerNotice }}</text>
        </view>

        <view class="question-book">
          <view class="question-book__head">
            <text class="question-book__title">题本区</text>
            <text class="question-book__meta">第 {{ questionBookIndex + 1 }} / {{ examStore.totalQuestions }} 题</text>
          </view>
          <swiper
            class="question-book__swiper"
            :current="questionBookIndex"
            :indicator-dots="examStore.totalQuestions > 1"
            indicator-color="rgba(255,255,255,0.35)"
            indicator-active-color="#ffffff"
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
                <text class="question-book__stem">{{ item.stem }}</text>
              </view>
            </swiper-item>
          </swiper>
        </view>
      </view>

      <scroll-view scroll-y class="question-panel">
        <view v-if="isJiangsuReading" class="card reading-list-card">
          <text class="reading-list__title">江苏 5+15 阅读题本</text>
          <text v-for="(item, index) in examStore.questions" :key="item.id || index" class="reading-list__item">
            {{ index + 1 }}. {{ item.stem }}
          </text>
        </view>

        <view class="card">
          <view class="section-head">
            <text class="section-title">作答区</text>
            <text class="muted">{{ useVideoMode ? '录像 / 录音' : '仅录音' }}</text>
          </view>

          <view class="media-toggle">
            <view class="media-toggle__item" :class="{ 'media-toggle__item--active': !useVideoMode }" @tap="setMediaMode('audio')">
              <text>仅录音</text>
            </view>
            <view class="media-toggle__item" :class="{ 'media-toggle__item--active': useVideoMode }" @tap="setMediaMode('video')">
              <text>录像+录音</text>
            </view>
          </view>

          <view class="text-answer-panel">
            <view class="section-head section-head--compact">
              <text class="section-title section-title--small">文字作答</text>
              <text class="muted">{{ answerText.length }} 字</text>
            </view>
            <textarea
              v-model="answerText"
              class="textarea-field"
              maxlength="-1"
              placeholder="请输入文字作答内容"
            />
          </view>

          <view v-if="useVideoMode" class="camera-panel">
            <!-- #ifdef MP-WEIXIN -->
            <camera
              class="camera-preview"
              mode="normal"
              device-position="front"
              flash="off"
              @error="onCameraError"
            />
            <!-- #endif -->
            <!-- #ifndef MP-WEIXIN -->
            <view class="camera-preview camera-preview--fallback">
              <text>当前运行环境不支持小程序摄像头组件</text>
            </view>
            <!-- #endif -->
            <view class="record-panel__status camera-panel__status">
              <text>{{ cameraStatusText }}</text>
              <text v-if="recordedVideoFile" class="record-panel__ready">已录像</text>
            </view>
            <view class="record-actions">
              <button
                class="secondary-button"
                :disabled="!cameraAvailable || videoRecording || recording || examStore.loading"
                @tap="startVideoRecord"
              >
                开始录像
              </button>
              <button
                class="secondary-button"
                :disabled="!videoRecording || examStore.loading"
                @tap="stopVideoRecord"
              >
                停止录像
              </button>
            </view>
          </view>

          <view class="record-panel">
            <view class="record-panel__status">
              <text>{{ recordStatusText }}</text>
              <text v-if="recordedFile" class="record-panel__ready">已录音</text>
            </view>
            <view class="record-actions">
              <button
                class="secondary-button"
                :disabled="recording || videoRecording || examStore.loading"
                @tap="startRecord"
              >
                开始录音
              </button>
              <button
                class="secondary-button"
                :disabled="!recording || examStore.loading"
                @tap="stopRecord"
              >
                停止录音
              </button>
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
import { computed, onBeforeUnmount, ref, watch } from 'vue'
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
const answerText = ref('')
const recording = ref(false)
const recordedFile = ref('')
const recorder = ref(null)
const videoRecording = ref(false)
const recordedVideoFile = ref('')
const cameraContext = ref(null)
const cameraError = ref('')
const cameraAvailable = ref(false)
const selectedMediaType = ref('')
const questionStartedAt = ref(Date.now())
const questionBookIndex = ref(0)
const reportedQuestionKeys = new Set()
const JIANGSU_MOCK_TIMING_MODE = 'jiangsu_5_15'
const JIANGSU_READING_SECONDS = 5 * 60
const JIANGSU_ANSWER_SECONDS = 15 * 60
let timer = null
let pendingRecordStopResolve = null

const question = computed(() => examStore.currentQuestion)
const useVideoMode = computed(() => examStore.mediaMode === 'video')
const isJiangsuMockTiming = computed(() => examStore.source === 'mock' && examStore.questions.some((item) => (
  item?.mockTimingMode === JIANGSU_MOCK_TIMING_MODE
)))
const isJiangsuReading = computed(() => isJiangsuMockTiming.value && phase.value === 'reading')
const activeTimeLeft = computed(() => (
  phase.value === 'preparing' || phase.value === 'reading' ? prepLeft.value : answerLeft.value
))
const activeTimerLabel = computed(() => {
  if (phase.value === 'reading') return '阅读'
  return phase.value === 'preparing' ? '准备' : '作答'
})
const provinceName = computed(() => getProvinceName(question.value?.province || 'national'))
const categoryName = computed(() => getCategoryName(question.value?.dimension || question.value?.type || ''))
const examinerNotice = computed(() => {
  if (isJiangsuReading.value) return '现在是题本阅读时间，请先通读全部题目，阅读结束后再开始作答。'
  if (phase.value === 'preparing') return '请利用准备时间梳理答题层次，作答开始后保持语速稳定。'
  if (recording.value || videoRecording.value) return '当前正在记录作答，请正面看向考官区，按结构完成表达。'
  return '请按顺序完成当前题目，答完后提交进入下一题。'
})
const cameraStatusText = computed(() => {
  if (!useVideoMode.value) return '已选择仅录音，不启用摄像头'
  if (cameraError.value) return cameraError.value
  if (videoRecording.value) return '摄像头录像中，请保持正对镜头'
  if (recordedVideoFile.value) return '录像已保存，可提交或重新录制'
  if (!cameraAvailable.value) return '当前环境暂不支持录像，可使用录音或文字提交'
  return '请授权摄像头，可使用录像提交作答'
})
const recordStatusText = computed(() => {
  if (recording.value) return '录音中，请保持语速稳定'
  if (recordedFile.value) return '录音已保存，可提交或重新录制'
  return '请授权麦克风，可使用录音提交作答'
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
  if (useVideoMode.value) setupCamera()
})

onHide(() => {
  if (videoRecording.value) stopVideoRecord({ silent: true })
})

onBeforeUnmount(() => {
  clearInterval(timer)
  if (recording.value) stopRecord()
  if (videoRecording.value) stopVideoRecord({ silent: true })
})

watch(() => examStore.currentIndex, (index) => {
  questionBookIndex.value = Math.max(0, Number(index) || 0)
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
    if (recordedFile.value) {
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

function setMediaMode(mode) {
  if (videoRecording.value) {
    toast('请先停止录像')
    return
  }
  examStore.setMediaMode(mode)
  if (mode === 'video') {
    setupCamera()
  } else {
    cameraError.value = ''
    recordedVideoFile.value = ''
    if (selectedMediaType.value === 'video') selectedMediaType.value = ''
  }
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
  answerText.value = ''
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
  if (examStore.source === 'mock') return 'mock'
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

function startRecord() {
  if (!canRecordNow()) return
  if (videoRecording.value) {
    toast('请先停止录像')
    return
  }
  if (!recorder.value) {
    toast('当前环境不支持录音')
    return
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
  } catch {
    toast('无法启动录音')
  }
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
  if (recording.value) {
    toast('请先停止录音')
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
      },
      fail(error) {
        videoRecording.value = false
        cameraAvailable.value = false
        const message = error?.errMsg || '无法启动摄像头录像'
        cameraError.value = message
        toast(message)
      }
    })
  } catch (error) {
    videoRecording.value = false
    cameraAvailable.value = false
    const message = error?.message || '无法启动摄像头录像'
    cameraError.value = message
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
  const visibleAnswerText = answerText.value

  showLoading(examStore.isLastQuestion ? '生成结果' : '保存作答')
  try {
    const answer = await examStore.submitCurrentAnswer({
      text: visibleAnswerText,
      filePath: media.filePath,
      mediaType: media.mediaType || 'audio'
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
        if (recording.value) stopRecord()
        if (videoRecording.value) stopVideoRecord({ silent: true })
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
  background: #0f2438;
}

.exam-room__body {
  display: flex;
  flex-direction: column;
  height: 100vh;
}

.exam-room__exit-fixed {
  position: fixed;
  top: calc(18rpx + env(safe-area-inset-top));
  right: 24rpx;
  z-index: 20;
  width: 96rpx;
  min-height: 58rpx;
  border: 1rpx solid rgba(255, 255, 255, 0.52);
  border-radius: 999rpx;
  background: rgba(13, 31, 48, 0.74);
  color: #ffffff;
  font-size: 24rpx;
  font-weight: 800;
}

.mock-scene {
  position: relative;
  height: 620rpx;
  overflow: hidden;
  background: #0f2438;
}

.mock-scene__image {
  position: absolute;
  inset: 0;
  width: 100%;
  height: 100%;
}

.mock-scene__shade {
  position: absolute;
  inset: 0;
  background:
    linear-gradient(180deg, rgba(4, 17, 30, 0.54) 0%, rgba(4, 17, 30, 0.1) 38%, rgba(4, 17, 30, 0.78) 100%),
    linear-gradient(90deg, rgba(4, 17, 30, 0.62) 0%, rgba(4, 17, 30, 0.06) 52%, rgba(4, 17, 30, 0.46) 100%);
}

.room-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16rpx;
  padding: calc(18rpx + env(safe-area-inset-top)) 140rpx 16rpx 28rpx;
}

.room-header--floating {
  position: relative;
  z-index: 2;
  color: #ffffff;
}

.room-header__count {
  display: block;
  color: #ffffff;
  font-size: 29rpx;
  font-weight: 800;
}

.room-header__sub {
  display: block;
  margin-top: 6rpx;
  color: rgba(255, 255, 255, 0.78);
  font-size: 22rpx;
}

.room-header__timer {
  padding: 8rpx 16rpx;
  border-radius: 999rpx;
  background: rgba(255, 255, 255, 0.92);
  color: #16385a;
  font-size: 25rpx;
  font-weight: 700;
  white-space: nowrap;
}

.examiner-panel {
  position: relative;
  z-index: 2;
  width: 62%;
  margin: 16rpx 0 0 28rpx;
  padding: 18rpx 20rpx;
  border: 1rpx solid rgba(255, 255, 255, 0.2);
  border-radius: 16rpx;
  background: rgba(13, 31, 48, 0.6);
  backdrop-filter: blur(8rpx);
}

.examiner-panel__kicker,
.examiner-panel__title,
.examiner-panel__desc {
  display: block;
}

.examiner-panel__kicker {
  color: #8fd0ff;
  font-size: 21rpx;
  font-weight: 800;
}

.examiner-panel__title {
  margin-top: 6rpx;
  color: #ffffff;
  font-size: 28rpx;
  font-weight: 900;
  line-height: 1.35;
}

.examiner-panel__desc {
  margin-top: 8rpx;
  color: rgba(255, 255, 255, 0.82);
  font-size: 23rpx;
  line-height: 1.55;
}

.question-book {
  position: absolute;
  right: 24rpx;
  bottom: 24rpx;
  left: 24rpx;
  z-index: 3;
  padding: 18rpx;
  border: 1rpx solid rgba(255, 255, 255, 0.22);
  border-radius: 18rpx;
  background: rgba(12, 30, 48, 0.78);
  box-shadow: 0 18rpx 48rpx rgba(0, 0, 0, 0.28);
}

.question-book__head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 12rpx;
}

.question-book__title {
  color: #ffffff;
  font-size: 27rpx;
  font-weight: 900;
}

.question-book__meta {
  color: rgba(255, 255, 255, 0.74);
  font-size: 23rpx;
  font-weight: 700;
}

.question-book__swiper {
  height: 230rpx;
}

.question-book__card {
  height: 194rpx;
  padding: 18rpx;
  border: 1rpx solid rgba(255, 255, 255, 0.14);
  border-radius: 14rpx;
  background: rgba(255, 255, 255, 0.95);
}

.question-book__card--current {
  border-color: #8fd0ff;
}

.question-book__stem {
  display: -webkit-box;
  max-height: 132rpx;
  overflow: hidden;
  color: #1f2b3d;
  font-size: 28rpx;
  font-weight: 700;
  line-height: 1.55;
  text-overflow: ellipsis;
  -webkit-box-orient: vertical;
  -webkit-line-clamp: 3;
}

.question-tag--active {
  background: #e6f7ff;
  color: #0958a5;
}

.question-panel {
  flex: 1;
  min-height: 0;
  padding: 24rpx 28rpx;
  background: #f0f5fa;
}

.question-stem {
  display: block;
  color: #1f2b3d;
  font-size: 31rpx;
  font-weight: 650;
  line-height: 1.75;
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

.section-head--compact {
  margin-bottom: 14rpx;
}

.section-title--small {
  font-size: 27rpx;
}

.text-answer-panel {
  margin-bottom: 22rpx;
}

.media-toggle {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 12rpx;
  margin-bottom: 20rpx;
}

.media-toggle__item {
  padding: 18rpx 14rpx;
  border: 1rpx solid #d9e3ef;
  border-radius: 14rpx;
  background: #ffffff;
  color: #2a3648;
  font-size: 25rpx;
  font-weight: 800;
  text-align: center;
}

.media-toggle__item--active {
  border-color: #1b5faa;
  background: #e8f4fd;
  color: #1b5faa;
}

.camera-preview--fallback {
  display: flex;
  align-items: center;
  justify-content: center;
  color: rgba(255, 255, 255, 0.76);
  font-size: 25rpx;
}

.camera-panel {
  overflow: hidden;
  border: 1rpx solid #d9e3ef;
  border-radius: 16rpx;
  background: #f6f8fb;
}

.camera-preview {
  display: block;
  width: 100%;
  height: 220rpx;
  background: #111827;
}

.camera-panel__status {
  padding: 18rpx 20rpx 0;
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

.record-actions {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 16rpx;
  margin-top: 18rpx;
}

.camera-panel .record-actions {
  padding: 0 20rpx 20rpx;
}

.room-actions {
  display: grid;
  grid-template-columns: 180rpx minmax(0, 1fr);
  gap: 16rpx;
  padding: 18rpx 28rpx calc(18rpx + env(safe-area-inset-bottom));
  border-top: 1rpx solid #e8eef5;
  background: #ffffff;
}

.exam-room__empty {
  padding: 30rpx;
}
</style>
