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
    <a-alert
      v-if="asrUnavailable"
      class="exam-prepare__asr-alert"
      type="warning"
      show-icon
      :message="asrStatusText"
    />

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
              <a-button size="small" v-if="micReady && !cameraReady" @click="tryMicOnly">仅使用麦克风</a-button>
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
              <span style="color: #389E0D">试录完成，可直接进入考场</span>
            </div>
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
        <div v-if="showPracticeConfig" class="practice-config">
          <div class="practice-config__item">
            <span class="practice-config__label">题目数量</span>
            <a-input-number
              v-model:value="questionCount"
              :min="1"
              :max="10"
              :disabled="isTrialEntry"
              style="width: 120px"
            />
          </div>
          <div class="practice-config__item">
            <span class="practice-config__label">题目类型</span>
            <a-select
              v-model:value="dimensionFilters"
              mode="multiple"
              placeholder="随机题型"
              style="width: 260px"
              :max-tag-count="2"
              @change="handleDimensionFiltersChange"
            >
              <a-select-option
                v-for="item in questionCategoryOptions"
                :key="item.key"
                :value="item.key"
                :disabled="item.key === RANDOM_DIMENSION_KEY && selectedSpecificDimensionCount > 0"
              >
                {{ item.name }}
              </a-select-option>
            </a-select>
          </div>
        </div>
      </div>
      <a-button type="primary" size="large" block :loading="enteringExam" :disabled="enteringExam || asrUnavailable" @click="enterExam" style="margin-top: 16px">
        {{ asrUnavailable ? '语音服务未就绪' : examMode === 'mock' ? '开始模拟面试' : '进入考场' }}
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
import { getAsrStatus } from '@/api/scoring'
import { useUserStore } from '@/stores/user'
import { useTargetedStore } from '@/stores/targeted'
import {
  getScoringUnavailableMessage,
  splitScoringSupportedQuestions
} from '@/utils/scoringSupport'

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
const videoEnabled = ref(true)
const examMode = ref('free')
const enteringExam = ref(false)
const questionCount = ref(5)
const dimensionFilters = ref(['random'])
const asrStatus = ref(null)

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
const DEFAULT_EXAM_QUESTION_COUNT = 5
const JIANGSU_MOCK_QUESTION_COUNT = 4
const JIANGSU_MOCK_TIMING_MODE = 'jiangsu_5_15'
const RANDOM_FETCH_BUFFER = 6
const RANDOM_FETCH_ATTEMPTS = 3
const RANDOM_DIMENSION_KEY = 'random'
const questionCategoryOptions = [
  { key: RANDOM_DIMENSION_KEY, name: '随机题型' },
  { key: 'analysis', name: '综合分析' },
  { key: 'practical', name: '组织管理' },
  { key: 'emergency', name: '应急应变' },
  { key: 'logic', name: '人际沟通' },
  { key: 'expression', name: '现场模拟' },
  { key: 'legal', name: '职业认知' }
]

const isTrialEntry = computed(() => String(route.query.trial || '') === '1' && !billingStore.isPaid)
const showPracticeConfig = computed(() => examMode.value === 'free')
const asrUnavailable = computed(() => asrStatus.value && asrStatus.value.ready === false)
const asrStatusText = computed(() => {
  if (!asrStatus.value) return ''
  return asrStatus.value.message || '语音转写服务未就绪，请联系管理员检查后端 Whisper/ffmpeg 配置。'
})
const selectedSpecificDimensions = computed(() => (
  dimensionFilters.value.filter((item) => item && item !== RANDOM_DIMENSION_KEY)
))
const selectedSpecificDimensionCount = computed(() => selectedSpecificDimensions.value.length)
const selectedDimensionParam = computed(() => selectedSpecificDimensions.value.join(','))
const mockQuestionCount = computed(() => (
  userStore.selectedProvince === 'jiangsu' ? JIANGSU_MOCK_QUESTION_COUNT : DEFAULT_EXAM_QUESTION_COUNT
))

function handleDimensionFiltersChange(values = []) {
  const selected = Array.isArray(values) ? values.filter(Boolean) : []
  const specific = selected.filter((item) => item !== RANDOM_DIMENSION_KEY)
  dimensionFilters.value = specific.length ? specific : [RANDOM_DIMENSION_KEY]
}

function applyUserPracticePreferencesToQuestions(questions = []) {
  const prefs = userStore.preferences || {}
  const prepTime = Number(prefs.defaultPrepTime || 0)
  const answerTime = Number(prefs.defaultAnswerTime || 0)
  return questions.map((question) => ({
    ...question,
    prepTime: prepTime || Number(question?.prepTime || 90),
    answerTime: answerTime || Number(question?.answerTime || 180)
  }))
}

function applyMockTimingMode(questions = []) {
  if (examMode.value !== 'mock' || userStore.selectedProvince !== 'jiangsu') return questions
  return questions.slice(0, JIANGSU_MOCK_QUESTION_COUNT).map((question) => ({
    ...question,
    mockTimingMode: JIANGSU_MOCK_TIMING_MODE
  }))
}

async function loadAsrStatus() {
  asrStatus.value = await getAsrStatus({ skipErrorHandler: true }).catch(() => null)
}

function notifyUnsupportedQuestions(unsupportedCount, replaced = false) {
  if (!unsupportedCount) return

  if (replaced) {
    message.warning(`已跳过 ${unsupportedCount} 道未接入评分题库的题目，并自动替换为可评分题目。`)
    return
  }

  message.warning(`已跳过 ${unsupportedCount} 道未接入评分题库的题目，本次仅保留可评分题目。`)
}

async function fetchScoringReadyRandomQuestions(count = DEFAULT_EXAM_QUESTION_COUNT, options = {}) {
  const targetCount = Math.max(Number(count) || 0, 0)
  const excludeIds = new Set(Array.isArray(options.excludeIds) ? options.excludeIds.filter(Boolean) : [])
  const collected = []

  for (let attempt = 0; attempt < RANDOM_FETCH_ATTEMPTS && collected.length < targetCount; attempt++) {
    const batch = await getRandomQuestions({
      province: userStore.selectedProvince,
      count: Math.max(targetCount + RANDOM_FETCH_BUFFER, targetCount),
      dimension: options.dimension ?? (examMode.value === 'free' ? selectedDimensionParam.value : ''),
      ...options.params
    })

    const { supported } = splitScoringSupportedQuestions(batch)
    for (const question of supported) {
      if (!question?.id || excludeIds.has(question.id)) continue
      excludeIds.add(question.id)
      collected.push(question)
      if (collected.length >= targetCount) break
    }
  }

  return collected.slice(0, targetCount)
}

async function ensureScoringReadyQuestions(questions, options = {}) {
  const candidateList = Array.isArray(questions) ? questions.filter(Boolean) : []
  const requiredCount = Math.max(Number(options.requiredCount) || 0, 0)
  const allowAutoSupplement = options.allowAutoSupplement !== false

  const { supported, unsupported } = splitScoringSupportedQuestions(candidateList)
  let resolved = [...supported]

  if (!resolved.length) {
    if (!allowAutoSupplement || !requiredCount) {
      message.error(getScoringUnavailableMessage(candidateList.length || 1))
      return []
    }

    const replacementQuestions = await fetchScoringReadyRandomQuestions(requiredCount)
    if (!replacementQuestions.length) {
      message.error('当前没有可用的评分题目，请稍后再试。')
      return []
    }

    notifyUnsupportedQuestions(candidateList.length || 1, true)
    return replacementQuestions
  }

  if (unsupported.length) {
    notifyUnsupportedQuestions(unsupported.length)
  }

  if (allowAutoSupplement && requiredCount && resolved.length < requiredCount) {
    const supplementQuestions = await fetchScoringReadyRandomQuestions(requiredCount - resolved.length, {
      excludeIds: resolved.map((question) => question?.id)
    })

    if (supplementQuestions.length) {
      resolved = [...resolved, ...supplementQuestions]
      message.info(`已自动补足 ${supplementQuestions.length} 道可评分题目。`)
    }
  }

  return resolved.slice(0, requiredCount || resolved.length)
}

onMounted(() => {
  loadAsrStatus().catch(() => null)
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
  currentStep.value = 0
  permissionError.value = ''
  const ok = await checkBoth()
  if (ok) {
    videoEnabled.value = true
    currentStep.value = 1
    await initRecorder()
    return
  }

  if (micReady.value && !cameraReady.value) {
    videoEnabled.value = false
    currentStep.value = 1
    await initRecorder()
  }
}

async function retryPermission() {
  permissionError.value = ''
  await doPermissionCheck()
}

async function tryMicOnly() {
  permissionError.value = ''
  currentStep.value = 0
  const ok = await checkMicOnly()
  if (ok) {
    videoEnabled.value = false
    currentStep.value = 1
    await initRecorder()
  }
}

async function initRecorder() {
  await recorder.initStream({ videoEnabled: videoEnabled.value })
}

function stepStatus(step) {
  if (step < currentStep.value) return 'finish'
  if (step === currentStep.value) return 'process'
  return 'wait'
}

async function startTestRecord() {
  testRecording.value = true
  testCountdown.value = 3
  recorder.startRecording()

  countdownTimer = setInterval(() => {
    testCountdown.value--
    if (testCountdown.value <= 0) {
      clearInterval(countdownTimer)
      finishTestRecord()
    }
  }, 1000)
}

async function finishTestRecord() {
  const blob = await recorder.stopRecording()
  testRecording.value = false
  testBlob.value = blob
  if (blob) {
    testBlobUrl.value = URL.createObjectURL(blob)
    currentStep.value = 2
    confirmDevice()
  }
}

function retryTest() {
  testBlob.value = null
  if (testBlobUrl.value) URL.revokeObjectURL(testBlobUrl.value)
  testBlobUrl.value = ''
  currentStep.value = 1
}

function confirmDevice() {
  allReady.value = true
  examStore.setDeviceReady(true)
}

async function enterExamLegacy() {
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

async function enterExam() {
  if (enteringExam.value) return

  await loadAsrStatus().catch(() => null)
  if (asrUnavailable.value) {
    message.warning('语音转写服务未就绪，请稍后重试。')
    return
  }

  enteringExam.value = true
  let questions = []
  const source = String(route.query.source || '')
  const recommendedId = String(route.query.questionId || '')
  const freeQuestionCount = Math.max(1, Math.min(10, Number(questionCount.value) || DEFAULT_EXAM_QUESTION_COUNT))
  const targetQuestionCount = isTrialEntry.value
    ? 1
    : examMode.value === 'mock'
      ? mockQuestionCount.value
      : freeQuestionCount

  try {
    if (isTrialEntry.value) {
      try {
        const trialQuestion = await getQuestionById(billingStore.trialQuestion.id)
        questions = trialQuestion ? [trialQuestion] : []
      } catch {
        message.error('试用题加载失败，请稍后重试。')
        return
      }
    } else if (source === 'targeted' && targetedStore.generatedQuestions.length) {
      questions = await ensureScoringReadyQuestions(targetedStore.generatedQuestions, {
        allowAutoSupplement: false
      })
    } else if (source === 'targeted' && recommendedId) {
      try {
        const cached = sessionStorage.getItem('targeted_question')
        const selectedQuestion = cached ? JSON.parse(cached) : await getQuestionById(recommendedId)
        questions = await ensureScoringReadyQuestions([selectedQuestion], {
          allowAutoSupplement: false
        })
      } catch {
        questions = await fetchScoringReadyRandomQuestions(targetQuestionCount)
      }
    } else if (source === 'training' && recommendedId) {
      try {
        const cached = sessionStorage.getItem('training_question')
        const selectedQuestion = cached ? JSON.parse(cached) : await getQuestionById(recommendedId)
        questions = await ensureScoringReadyQuestions([selectedQuestion], {
          allowAutoSupplement: false
        })
      } catch {
        questions = await fetchScoringReadyRandomQuestions(targetQuestionCount)
      }
    } else if (recommendedId) {
      try {
        const question = await getQuestionById(recommendedId)
        questions = await ensureScoringReadyQuestions([question], { requiredCount: 1 })
      } catch {
        questions = await fetchScoringReadyRandomQuestions(targetQuestionCount)
      }
    } else {
      questions = await fetchScoringReadyRandomQuestions(targetQuestionCount)
    }

    if (!questions.length) {
      userStore.requireProvinceSelection(true)
      message.warning('当前省份暂无可用题目，请先重新选择省份。')
      return
    }

    questions = applyMockTimingMode(applyUserPracticePreferencesToQuestions(questions))

    recorder.destroyStream()
    examStore.setVideoEnabled(videoEnabled.value)

    if (examMode.value === 'mock') {
      if (isTrialEntry.value) {
        await examStore.initExam(questions, true)
        router.push('/exam/room')
        return
      }

      pendingQuestions = questions
      waitingRoom.value = true
      waitSeconds.value = 10
      clearInterval(waitTimer)
      waitTimer = setInterval(async () => {
        waitSeconds.value -= 1
        if (waitSeconds.value <= 0) {
          clearInterval(waitTimer)
          await startMockExam(pendingQuestions)
        }
      }, 1000)
      return
    }

    await examStore.initExam(questions, false)
    router.push('/exam/room')
  } catch (error) {
    message.error(error?.normalizedMessage || error?.message || '进入考场失败，请稍后重试。')
  } finally {
    enteringExam.value = false
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

.exam-prepare__asr-alert {
  margin-bottom: 18px;
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

.practice-config {
  display: grid;
  gap: 14px;
  margin-top: 16px;
  padding-top: 16px;
  border-top: 1px solid @border-color;
}

.practice-config__item {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
}

.practice-config__label {
  flex: 0 0 auto;
  color: @text-primary;
  font-weight: 600;
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
