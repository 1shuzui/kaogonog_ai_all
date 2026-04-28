<template>
  <div class="exam-prepare page-container">
    <!-- 候考室倒计时 -->
    <div v-if="waitingRoom" class="waiting-room card">
      <div class="waiting-room__icon">🏛️</div>
      <h2>候考室</h2>
      <p class="waiting-room__hint">模拟面试即将开始，请做好准备</p>
      <div class="waiting-room__countdown">{{ waitCountdown }}</div>
      <p class="waiting-room__tip">提示：调整坐姿，保持自信微笑，深呼吸放松</p>
      <a-button type="text" @click="skipWaiting">跳过等待</a-button>
    </div>

    <!-- 正常设备检测流程 -->
    <template v-else>
    <h2 class="exam-prepare__title">设备检测</h2>
    <p class="exam-prepare__desc">开始测评前，请确认摄像头和麦克风正常工作</p>

    <a-steps :current="currentStep" direction="vertical" class="exam-prepare__steps">
      <a-step title="设备权限检测" :status="stepStatus(0)">
        <template #description>
          <div v-if="currentStep === 0 && !permissionError">
            <a-spin size="small" /> 正在请求设备权限...
          </div>
          <div v-else-if="currentStep === 0 && permissionError">
            <p style="color: #CF1322; margin-bottom: 8px">{{ permissionError }}</p>
            <a-space>
              <a-button size="small" type="primary" @click="retryPermission">重新检测</a-button>
              <a-button size="small" v-if="!micReady" @click="tryMicOnly">仅使用麦克风</a-button>
            </a-space>
            <div class="permission-tips">
              <p>常见原因:</p>
              <ul>
                <li>麦克风/摄像头被其他程序(如腾讯会议、微信)占用，请先关闭</li>
                <li>浏览器未授权，请点击地址栏左侧锁图标 → 允许麦克风和摄像头</li>
                <li>系统设置中麦克风被禁用 (Windows: 设置 → 隐私 → 麦克风)</li>
              </ul>
            </div>
          </div>
          <div v-else-if="currentStep > 0">
            <span style="color: #389E0D" v-if="cameraReady && micReady">摄像头和麦克风已就绪</span>
            <span style="color: #389E0D" v-else-if="micReady">麦克风已就绪 (仅语音模式)</span>
          </div>
        </template>
      </a-step>
      <a-step title="试录 3 秒" :status="stepStatus(1)">
        <template #description>
          <div v-if="currentStep === 1">
            <a-button v-if="!testRecording && !testBlob" size="small" type="primary" @click="startTestRecord">
              开始试录
            </a-button>
            <span v-else-if="testRecording" style="color: #D48806">录制中... {{ testCountdown }}s</span>
            <span v-else-if="testBlob" style="color: #389E0D">试录完成</span>
          </div>
        </template>
      </a-step>
      <a-step title="回放确认" :status="stepStatus(2)">
        <template #description>
          <div v-if="currentStep === 2 && testBlobUrl">
            <video v-if="cameraReady" :src="testBlobUrl" controls style="width: 100%; max-width: 300px; border-radius: 8px; margin-top: 8px"></video>
            <audio v-else :src="testBlobUrl" controls style="width: 100%; max-width: 300px; margin-top: 8px"></audio>
            <div style="margin-top: 8px">
              <a-button size="small" @click="retryTest" style="margin-right: 8px">重新试录</a-button>
              <a-button size="small" type="primary" @click="confirmDevice">确认正常</a-button>
            </div>
          </div>
          <div v-else-if="currentStep === 2 && allReady" style="color: #389E0D">
            设备检测已确认，可直接进入考场。
          </div>
        </template>
      </a-step>
    </a-steps>

    <!-- 模式选择 & 进入考场 -->
    <div class="exam-prepare__actions" v-if="allReady">
      <div class="mode-select card">
        <h4 style="margin-bottom: 12px">选择练习模式</h4>
        <a-radio-group v-model:value="examMode" style="width: 100%">
          <a-space direction="vertical" style="width: 100%">
            <a-radio value="free" class="mode-radio">
              <span class="mode-label">自由练习</span>
              <span class="mode-desc">随时暂停，自定义节奏</span>
            </a-radio>
            <a-radio value="mock" class="mode-radio">
              <span class="mode-label">模拟面试</span>
              <span class="mode-desc">候考等待 → 连续作答 → 全程计时，贴近真实考场</span>
            </a-radio>
          </a-space>
        </a-radio-group>
      </div>
      <a-button type="primary" size="large" block @click="enterExam" style="margin-top: 16px">
        {{ examMode === 'mock' ? '开始模拟面试' : '进入考场' }}
      </a-button>
    </div>
    </template>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onUnmounted } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { message } from 'ant-design-vue'
import { usePermission } from '@/composables/usePermission'
import { useMediaRecorder } from '@/composables/useMediaRecorder'
import { useExamStore } from '@/stores/exam'
import { useBillingStore } from '@/stores/billing'
import { getRandomQuestions, getQuestionById } from '@/api/questionBank'
import { useUserStore } from '@/stores/user'
import { useTargetedStore } from '@/stores/targeted'

const router = useRouter()
const route = useRoute()
const examStore = useExamStore()
const billingStore = useBillingStore()
const userStore = useUserStore()
const targetedStore = useTargetedStore()

const { cameraReady, micReady, error: permissionError, checkBoth, checkMicOnly } = usePermission()
const recorder = useMediaRecorder()

const currentStep = ref(0)
const testRecording = ref(false)
const testBlob = ref(null)
const testBlobUrl = ref('')
const testCountdown = ref(3)
const allReady = ref(false)
const recorderReady = ref(false)
const videoEnabled = ref(true)
const examMode = ref('free')

// 候考室
const waitingRoom = ref(false)
const waitSeconds = ref(10)
const waitCountdown = computed(() => {
  const m = Math.floor(waitSeconds.value / 60)
  const s = waitSeconds.value % 60
  return `${String(m).padStart(2, '0')}:${String(s).padStart(2, '0')}`
})

let countdownTimer = null
let waitTimer = null
let pendingQuestions = null

onMounted(() => {
  if (examStore.deviceReady) {
    restorePreparationState()
    return
  }
  doPermissionCheck()
})

onUnmounted(() => {
  clearInterval(countdownTimer)
  clearInterval(waitTimer)
  recorder.destroyStream()
  if (testBlobUrl.value) {
    URL.revokeObjectURL(testBlobUrl.value)
  }
})

async function doPermissionCheck() {
  resetPreparationState({ clearStoreReady: true })
  currentStep.value = 0
  permissionError.value = ''
  const ok = await checkBoth()
  if (ok) {
    videoEnabled.value = true
    const ready = await initRecorder()
    if (ready) {
      currentStep.value = 1
      return
    }
    permissionError.value = recorder.error.value || '录制设备初始化失败，请重试'
  }
}

async function retryPermission() {
  permissionError.value = ''
  await doPermissionCheck()
}

async function tryMicOnly() {
  resetPreparationState({ clearStoreReady: true })
  permissionError.value = ''
  currentStep.value = 0
  const ok = await checkMicOnly()
  if (ok) {
    videoEnabled.value = false
    const ready = await initRecorder()
    if (ready) {
      currentStep.value = 1
      return
    }
    permissionError.value = recorder.error.value || '录制设备初始化失败，请重试'
  }
}

async function initRecorder() {
  recorderReady.value = false
  const stream = await recorder.initStream({ videoEnabled: videoEnabled.value })
  recorderReady.value = !!stream
  return recorderReady.value
}

function stepStatus(step) {
  if (step < currentStep.value) return 'finish'
  if (step === currentStep.value) return 'process'
  return 'wait'
}

async function startTestRecord() {
  if (testRecording.value) return

  if (!recorderReady.value) {
    const ready = await initRecorder()
    if (!ready) {
      message.error(recorder.error.value || '录制设备初始化失败，请重新检测')
      return
    }
  }

  const started = recorder.startRecording()
  if (!started) {
    message.error(recorder.error.value || '开始试录失败，请重试')
    return
  }

  clearInterval(countdownTimer)
  testRecording.value = true
  testBlob.value = null
  if (testBlobUrl.value) {
    URL.revokeObjectURL(testBlobUrl.value)
    testBlobUrl.value = ''
  }
  testCountdown.value = 3

  countdownTimer = setInterval(() => {
    testCountdown.value--
    if (testCountdown.value <= 0) {
      clearInterval(countdownTimer)
      countdownTimer = null
      finishTestRecord()
    }
  }, 1000)
}

async function finishTestRecord() {
  const blob = await recorder.stopRecording()
  testRecording.value = false
  testBlob.value = blob
  if (!blob) {
    currentStep.value = 1
    message.warning('本次试录未生成有效录音，请重新试录')
    return
  }

  testBlobUrl.value = URL.createObjectURL(blob)
  currentStep.value = 2
}

function retryTest() {
  clearInterval(countdownTimer)
  countdownTimer = null
  testBlob.value = null
  if (testBlobUrl.value) URL.revokeObjectURL(testBlobUrl.value)
  testBlobUrl.value = ''
  testRecording.value = false
  testCountdown.value = 3
  currentStep.value = 1
}

function confirmDevice() {
  allReady.value = true
  examStore.setVideoEnabled(videoEnabled.value)
  examStore.setDeviceReady(true)
}

function resetPreparationState({ clearStoreReady = false } = {}) {
  clearInterval(countdownTimer)
  countdownTimer = null
  allReady.value = false
  recorderReady.value = false
  testRecording.value = false
  testBlob.value = null
  testCountdown.value = 3
  if (testBlobUrl.value) {
    URL.revokeObjectURL(testBlobUrl.value)
    testBlobUrl.value = ''
  }
  if (clearStoreReady) {
    examStore.setDeviceReady(false)
  }
}

function restorePreparationState() {
  resetPreparationState()
  allReady.value = true
  currentStep.value = 2
  permissionError.value = ''
  videoEnabled.value = examStore.videoEnabled
  micReady.value = true
  cameraReady.value = examStore.videoEnabled
}

async function enterExam() {
  recorder.destroyStream()
  // 保存视频模式到 store，供 ExamRoom 使用
  examStore.setVideoEnabled(videoEnabled.value)
  let questions
  const isTrialEntry = String(route.query.trial || '') === '1'
  const source = route.query.source
  const recommendedId = route.query.questionId

  if (isTrialEntry) {
    try {
      const trialQuestion = await getQuestionById(billingStore.trialQuestion.id)
      questions = [trialQuestion]
    } catch {
      questions = await getRandomQuestions({ province: userStore.selectedProvince, count: 1 })
    }
  } else if (source === 'targeted' && targetedStore.generatedQuestions.length) {
    // 来自定向备面（批量），使用已生成的题目
    questions = targetedStore.generatedQuestions
  } else if (source === 'targeted' && recommendedId) {
    // 来自定向备面（单题），从 sessionStorage 获取
    try {
      const cached = sessionStorage.getItem('targeted_question')
      questions = cached ? [JSON.parse(cached)] : [await getQuestionById(recommendedId)]
    } catch {
      questions = await getRandomQuestions({ province: userStore.selectedProvince, count: 5 })
    }
  } else if (source === 'training' && recommendedId) {
    // 来自专项训练，从 sessionStorage 获取
    try {
      const cached = sessionStorage.getItem('training_question')
      questions = cached ? [JSON.parse(cached)] : [await getQuestionById(recommendedId)]
    } catch {
      questions = await getRandomQuestions({ province: userStore.selectedProvince, count: 5 })
    }
  } else if (recommendedId) {
    // 从智能推荐跳转，使用指定题目
    try {
      const q = await getQuestionById(recommendedId)
      questions = [q]
    } catch {
      questions = await getRandomQuestions({
        province: userStore.selectedProvince,
        count: 5
      })
    }
  } else {
    questions = await getRandomQuestions({
      province: userStore.selectedProvince,
      count: 5
    })
  }

  if (examMode.value === 'mock') {
    await examStore.initExam(questions, true)
    router.push('/exam/room')
  } else {
    await examStore.initExam(questions, false)
    router.push('/exam/room')
  }
}

async function skipWaiting() {
  clearInterval(waitTimer)
  await startMockExam(pendingQuestions)
}

async function startMockExam(questions) {
  waitingRoom.value = false
  await examStore.initExam(questions, true)
  router.push('/exam/room')
}
</script>

<style lang="less" scoped>
@import '@/styles/variables.less';

.exam-prepare__title {
  font-size: @font-size-xxl;
  color: @text-primary;
  margin-bottom: 8px;
}

.exam-prepare__desc {
  color: @text-secondary;
  margin-bottom: 24px;
}

.exam-prepare__steps {
  margin-bottom: 24px;
}

.exam-prepare__actions {
  margin-top: 24px;
}

.mode-select {
  padding: 16px;

  h4 {
    font-size: @font-size-lg;
    color: @text-primary;
  }
}

.mode-radio {
  display: flex;
  align-items: flex-start;
  padding: 8px 0;
}

.mode-label {
  font-weight: 600;
  color: @text-primary;
  margin-right: 8px;
}

.mode-desc {
  font-size: @font-size-xs;
  color: @text-secondary;
}

.waiting-room {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  min-height: 60vh;
  text-align: center;
  padding: 40px 24px;

  h2 {
    font-size: @font-size-xxl;
    color: @text-primary;
    margin: 16px 0 8px;
  }
}

.waiting-room__icon {
  font-size: 64px;
}

.waiting-room__hint {
  color: @text-secondary;
  margin-bottom: 24px;
}

.waiting-room__countdown {
  font-size: 56px;
  font-weight: 700;
  color: @primary-color;
  font-variant-numeric: tabular-nums;
  margin-bottom: 16px;
}

.waiting-room__tip {
  font-size: @font-size-sm;
  color: @text-secondary;
  max-width: 300px;
  line-height: 1.6;
  margin-bottom: 16px;
}

.permission-tips {
  margin-top: 12px;
  padding: 12px;
  background: #FFF7E6;
  border-radius: 6px;
  font-size: @font-size-sm;
  color: @text-regular;

  p {
    font-weight: 600;
    margin-bottom: 4px;
  }
  ul {
    padding-left: 18px;
    margin: 0;
    li {
      line-height: 1.8;
    }
  }
}
</style>
