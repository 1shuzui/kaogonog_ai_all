<template>
  <view class="exam-room">
    <view v-if="question" class="exam-room__body">
      <view class="room-header">
        <text class="room-header__count">第 {{ examStore.questionNumber }} / {{ examStore.totalQuestions }} 题</text>
        <text class="room-header__timer">{{ activeTimerLabel }} {{ formatTime(activeTimeLeft) }}</text>
      </view>

      <scroll-view scroll-y class="question-panel">
        <view class="card">
          <text class="question-stem">{{ question.stem }}</text>
          <view v-if="points.length" class="points-mini">
            <text v-for="(point, index) in points" :key="index" class="points-mini__item">
              {{ index + 1 }}. {{ point.content || point.name }}
            </text>
          </view>
        </view>

        <view class="card">
          <view class="section-head">
            <text class="section-title">作答区</text>
            <text class="muted">{{ answerText.length }} 字</text>
          </view>
          <textarea
            v-model="answerText"
            class="textarea-field"
            maxlength="-1"
            placeholder="可以直接输入文字作答；如果已录音且不输入文字，系统会先转写录音。"
          />

          <view class="record-panel">
            <view class="record-panel__status">
              <text>{{ recordStatusText }}</text>
              <text v-if="recordedFile" class="record-panel__ready">已录音</text>
            </view>
            <view class="record-actions">
              <button
                class="secondary-button"
                :disabled="recording || examStore.loading"
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
import { computed, onBeforeUnmount, ref } from 'vue'
import { onLoad } from '@dcloudio/uni-app'
import EmptyState from '../../components/EmptyState.vue'
import { useExamStore } from '../../stores/exam'
import { useUserStore } from '../../stores/user'
import { formatTime } from '../../utils/format'
import { hideLoading, showLoading, toast } from '../../utils/navigation'

const examStore = useExamStore()
const userStore = useUserStore()
const phase = ref('preparing')
const prepLeft = ref(userStore.preferences.defaultPrepTime)
const answerLeft = ref(userStore.preferences.defaultAnswerTime)
const answerText = ref('')
const recording = ref(false)
const recordedFile = ref('')
const recorder = ref(null)
let timer = null

const question = computed(() => examStore.currentQuestion)
const points = computed(() => Array.isArray(question.value?.scoringPoints) ? question.value.scoringPoints.slice(0, 6) : [])
const activeTimeLeft = computed(() => phase.value === 'preparing' ? prepLeft.value : answerLeft.value)
const activeTimerLabel = computed(() => phase.value === 'preparing' ? '准备' : '作答')
const recordStatusText = computed(() => {
  if (recording.value) return '录音中，请保持语速稳定'
  if (recordedFile.value) return '录音已保存，可提交或重新录制'
  return '可使用麦克风录音，也可只提交文字'
})

onLoad(() => {
  setupRecorder()
  resetQuestionState()
  startTimer()
})

onBeforeUnmount(() => {
  clearInterval(timer)
  if (recording.value) stopRecord()
})

function setupRecorder() {
  if (typeof uni.getRecorderManager !== 'function') return
  recorder.value = uni.getRecorderManager()
  recorder.value.onStop((res) => {
    recording.value = false
    recordedFile.value = res.tempFilePath || ''
    if (recordedFile.value) toast('录音已保存', 'success')
  })
  recorder.value.onError((error) => {
    recording.value = false
    toast(error?.errMsg || '录音失败')
  })
}

function startTimer() {
  clearInterval(timer)
  timer = setInterval(() => {
    if (phase.value === 'preparing') {
      prepLeft.value -= 1
      if (prepLeft.value <= 0) phase.value = 'answering'
      return
    }
    answerLeft.value = Math.max(0, answerLeft.value - 1)
  }, 1000)
}

function resetQuestionState() {
  phase.value = 'preparing'
  prepLeft.value = Number(question.value?.prepTime || userStore.preferences.defaultPrepTime || 90)
  answerLeft.value = Number(question.value?.answerTime || userStore.preferences.defaultAnswerTime || 180)
  answerText.value = ''
  recording.value = false
  recordedFile.value = ''
}

function startRecord() {
  if (!recorder.value) {
    toast('当前环境不支持录音，请使用文字作答')
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

async function submitAnswer() {
  if (recording.value) {
    toast('请先停止录音')
    return
  }
  if (!answerText.value.trim() && !recordedFile.value) {
    toast('请先录音或输入文字作答')
    return
  }

  showLoading('提交评分')
  try {
    const answer = await examStore.submitCurrentAnswer({
      text: answerText.value,
      filePath: recordedFile.value
    })

    if (examStore.isLastQuestion) {
      await examStore.finish()
      uni.redirectTo({
        url: `/pages/result/index?examId=${encodeURIComponent(examStore.examId)}&questionId=${encodeURIComponent(answer.questionId)}`
      })
      return
    }

    uni.showModal({
      title: '本题已提交',
      content: '是否进入下一题？',
      confirmText: '下一题',
      cancelText: '看结果',
      success(res) {
        if (res.confirm) {
          examStore.goNext()
          resetQuestionState()
        } else {
          uni.navigateTo({
            url: `/pages/result/index?examId=${encodeURIComponent(examStore.examId)}&questionId=${encodeURIComponent(answer.questionId)}`
          })
        }
      }
    })
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
  background: #f0f5fa;
}

.exam-room__body {
  display: flex;
  flex-direction: column;
  height: 100vh;
}

.room-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 22rpx 28rpx;
  border-bottom: 1rpx solid #e8eef5;
  background: #ffffff;
}

.room-header__count {
  color: #1a1a2e;
  font-size: 29rpx;
  font-weight: 800;
}

.room-header__timer {
  padding: 8rpx 16rpx;
  border-radius: 999rpx;
  background: #e8f4fd;
  color: #1b5faa;
  font-size: 25rpx;
  font-weight: 700;
}

.question-panel {
  flex: 1;
  min-height: 0;
  padding: 24rpx 28rpx;
}

.question-stem {
  display: block;
  color: #1f2b3d;
  font-size: 31rpx;
  font-weight: 650;
  line-height: 1.75;
}

.points-mini {
  margin-top: 22rpx;
  padding-top: 18rpx;
  border-top: 1rpx solid #eef2f6;
}

.points-mini__item {
  display: block;
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
  border-top: 1rpx solid #e8eef5;
  background: #ffffff;
}

.exam-room__empty {
  padding: 30rpx;
}
</style>
