<!--
考试准备页，负责选择练习模式、套题和筛选条件，并在进入考场前确认权限与抽题结果。

准备页只做进入考场前的确认：全真模拟优先使用真实套题，定向练习沿用目标筛选；题目分值和评分反馈仍只在结果页展示。

@param: 无；模式、地区、年份和套题条件来自路由、用户偏好和页面选择。
@return: 渲染候考信息、筛选器、媒体检查、权益提示和进入考场按钮。
@raises: 不主动抛业务异常；权益不足、抽题失败或媒体权限异常由页面提示承接。
-->
<template>
  <div class="exam-prepare page-container">
    <!-- 候考室倒计时 -->
    <div v-if="waitingRoom" class="waiting-room card">
      <div class="waiting-room__icon">🏛️</div>
      <h2>候考室</h2>
      <p class="waiting-room__hint">全真模拟即将开始，请做好准备</p>
      <div class="waiting-room__countdown">{{ waitCountdown }}</div>
      <p class="waiting-room__tip">提示：调整坐姿，保持自信微笑，深呼吸放松</p>
      <a-space class="waiting-room__actions">
        <a-button danger @click="exitWaitingRoom">退出候考</a-button>
        <a-button type="primary" @click="skipWaiting">跳过等待</a-button>
      </a-space>
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
        <h4 style="margin-bottom: 12px">{{ isFixedPracticeEntry ? '专项练习' : '选择练习模式' }}</h4>
        <a-radio-group v-if="!isFixedPracticeEntry" v-model:value="examMode" style="width: 100%">
          <a-space direction="vertical" style="width: 100%">
            <a-radio value="free" class="mode-radio">
              <span class="mode-label">专项练习</span>
              <span class="mode-desc">适合专项训练和即时复盘</span>
            </a-radio>
            <a-radio value="fullExam" class="mode-radio">
              <span class="mode-label">全真模拟</span>
              <span class="mode-desc">按真题套卷连续作答，保留真实题序和考试节奏</span>
            </a-radio>
          </a-space>
        </a-radio-group>
        <div v-else class="fixed-practice-mode">
          <span class="mode-label">专项练习</span>
          <span class="mode-desc">已使用当前生成题目进入练习</span>
        </div>
        <div v-if="examMode === 'fullExam'" class="practice-config">
          <div class="practice-config__item">
            <span class="practice-config__label">真题套卷</span>
            <a-select
              v-model:value="selectedFullExamSuiteId"
              placeholder="选择整套真题"
              style="width: 320px"
              :disabled="fullExamSuitesLoading || !fullExamSuiteOptions.length"
            >
              <a-select-option
                v-for="suite in fullExamSuiteOptions"
                :key="suite.id"
                :value="suite.id"
              >
                {{ suite.title }}
              </a-select-option>
            </a-select>
          </div>
          <div class="practice-config__meta">
            {{ selectedFullExamSuite ? selectedFullExamSuiteSummary : (fullExamSuitesLoading ? '正在加载真题套卷...' : '当前省份暂无整套真题套卷，请切换江苏、安徽或湖南。') }}
          </div>
        </div>
        <div v-if="showTargetFilterConfig" class="practice-config">
          <div class="practice-config__item">
            <span class="practice-config__label">考试大类</span>
            <a-select
              v-model:value="selectedExamCategoryId"
              placeholder="不限"
              allow-clear
              style="width: 260px"
              @change="handleExamCategoryFilterChange"
            >
              <a-select-option v-for="cat in examCategoryOptions" :key="cat.id" :value="cat.id">
                {{ cat.name }}
              </a-select-option>
            </a-select>
          </div>
          <div class="practice-config__item">
            <span class="practice-config__label">地区</span>
            <a-select
              v-model:value="selectedRegionId"
              placeholder="不限"
              allow-clear
              style="width: 260px"
              :disabled="!regionOptions.length"
              @change="handleRegionFilterChange"
            >
              <a-select-option v-for="region in regionOptions" :key="region.id" :value="region.id">
                {{ region.name }}
              </a-select-option>
            </a-select>
          </div>
          <div v-if="hasDirectionOptions" class="practice-config__item">
            <span class="practice-config__label">方向</span>
            <a-select
              v-model:value="selectedDirectionId"
              placeholder="不限"
              allow-clear
              style="width: 260px"
              @change="handleDirectionFilterChange"
            >
              <a-select-option v-for="dir in directionOptions" :key="dir.id" :value="dir.id">
                {{ dir.name }}
              </a-select-option>
            </a-select>
          </div>
          <div v-if="showPracticeConfig" class="practice-config__item">
            <span class="practice-config__label">年份</span>
            <a-select
              v-model:value="selectedYearsFilter"
              mode="multiple"
              placeholder="不限年份"
              allow-clear
              style="width: 260px"
              :max-tag-count="2"
            >
              <a-select-option v-for="y in YEAR_OPTIONS" :key="y" :value="y">{{ y }}</a-select-option>
            </a-select>
          </div>
          <div v-if="showPracticeConfig" class="practice-config__item">
            <span class="practice-config__label">题目数量</span>
            <a-input-number
              v-model:value="questionCount"
              :min="1"
              :max="10"
              :disabled="isTrialEntry"
              style="width: 120px"
            />
          </div>
          <div v-if="showPracticeConfig" class="practice-config__item">
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
        {{ asrUnavailable ? '语音服务未就绪' : examMode === 'fullExam' ? '开始全真模拟' : '进入考场' }}
      </a-button>
    </div>
    </template>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onUnmounted, watch } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { message } from 'ant-design-vue'
import { usePermission } from '@/composables/usePermission'
import { useMediaRecorder } from '@/composables/useMediaRecorder'
import { useExamStore } from '@/stores/exam'
import { useBillingStore } from '@/stores/billing'
import { getRandomQuestions, getQuestionById, getQuestions } from '@/api/questionBank'
import { getAsrStatus } from '@/api/scoring'
import { useUserStore } from '@/stores/user'
import { useTargetedStore } from '@/stores/targeted'
import { hasPremiumAccess } from '@/utils/access'
import {
  getScoringUnavailableMessage,
  splitScoringSupportedQuestions
} from '@/utils/scoringSupport'
import {
  fetchFullExamSuites,
  getFullExamSuiteSummary,
  loadFullExamSuiteQuestions,
  normalizeProvinceCode
} from '@/utils/fullExamSuites'
import { parseTimingFormat, DEFAULT_TARGETED_POSITION_TREE } from '@/utils/targetedOptions'
import { YEAR_OPTIONS } from '@/utils/constants'

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
const questionTypeTouched = ref(false)
// Targeted filter state
const selectedExamCategoryId = ref('')
const selectedRegionId = ref('')
const selectedDirectionId = ref('')
const selectedYearsFilter = ref([])
const asrStatus = ref(null)
const selectedFullExamSuiteId = ref('')
const fullExamSuites = ref([])
const fullExamSuitesLoading = ref(false)

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
const JIANGSU_FULL_EXAM_TIMING_MODE = 'jiangsu_5_15'
const RANDOM_FETCH_BUFFER = 6
const RANDOM_FETCH_ATTEMPTS = 3
const RANDOM_DIMENSION_KEY = 'random'
const questionCategoryOptions = [
  { key: RANDOM_DIMENSION_KEY, name: '随机题型' },
  { key: 'analysis', name: '综合分析' },
  { key: 'practical', name: '组织管理' },
  { key: 'emergency', name: '应急应变' },
  { key: 'logic', name: '人际沟通' },
  { key: 'expression', name: '情景模拟' },
  { key: 'legal', name: '岗位认知' }
]

const hasFullAccess = computed(() => hasPremiumAccess(userStore, billingStore))
const isTrialEntry = computed(() => String(route.query.trial || '') === '1' && !hasFullAccess.value)
const fixedPracticeSources = new Set(['targeted', 'training', 'jiangsu'])
const source = computed(() => String(route.query.source || ''))
const isFixedPracticeEntry = computed(() => fixedPracticeSources.has(source.value))
const showPracticeConfig = computed(() => examMode.value === 'free' && !isFixedPracticeEntry.value)
const showTargetFilterConfig = computed(() => !isFixedPracticeEntry.value && ['free', 'fullExam'].includes(examMode.value))
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
const fullExamSuiteOptions = computed(() => fullExamSuites.value)
const selectedFullExamSuite = computed(() => (
  fullExamSuiteOptions.value.find((suite) => suite.id === selectedFullExamSuiteId.value)
  || fullExamSuiteOptions.value[0]
  || null
))
const selectedFullExamSuiteSummary = computed(() => getFullExamSuiteSummary(selectedFullExamSuite.value))

// Targeted filter computed properties
const examCategoryOptions = computed(() =>
  DEFAULT_TARGETED_POSITION_TREE.map(cat => ({ id: cat.id, name: cat.name }))
)
const selectedCategoryNode = computed(() =>
  selectedExamCategoryId.value
    ? DEFAULT_TARGETED_POSITION_TREE.find(c => String(c.id) === String(selectedExamCategoryId.value)) || null
    : null
)
function uniqueRegionsFromTree() {
  const seen = new Set()
  const regions = []
  DEFAULT_TARGETED_POSITION_TREE.forEach((category) => {
    ;(category.children || []).forEach((region) => {
      const province = normalizeProvinceCode(region.province || '')
      if (!province || province === 'all') return
      if (seen.has(province)) return
      seen.add(province)
      regions.push({
        id: `region_${province}`,
        name: region.name || province,
        province
      })
    })
  })
  return regions
}
const regionOptions = computed(() => uniqueRegionsFromTree())
const selectedRegionNode = computed(() =>
  selectedRegionId.value
    ? regionOptions.value.find(r => String(r.id) === String(selectedRegionId.value)) || null
    : null
)
function findCategoryByPreference(value = '') {
  const text = String(value || '').trim()
  if (!text) return null
  return DEFAULT_TARGETED_POSITION_TREE.find((category) => (
    String(category.id) === text
    || String(category.name) === text
    || String(category.examCategory || '') === text
  )) || null
}
function matchingTreeRegions() {
  const region = selectedRegionNode.value
  if (!region) return []
  const categories = selectedCategoryNode.value ? [selectedCategoryNode.value] : DEFAULT_TARGETED_POSITION_TREE
  return categories.flatMap((category) => (
    (category.children || []).filter((item) => normalizeProvinceCode(item.province || '') === region.province)
  ))
}
const hasDirectionOptions = computed(() =>
  directionOptions.value.length > 0
)
const directionOptions = computed(() => {
  const seen = new Set()
  const options = []
  matchingTreeRegions().forEach((region) => {
    const directions = Array.isArray(region.directions)
      ? region.directions
      : Array.isArray(region.children)
        ? region.children
        : []
    directions.forEach((direction) => {
      const id = String(direction.id || `${region.id}_${direction.name}`)
      if (seen.has(id)) return
      seen.add(id)
      options.push(direction)
    })
  })
  return options
})
const selectedDirectionNode = computed(() =>
  selectedDirectionId.value
    ? directionOptions.value.find(d => String(d.id) === String(selectedDirectionId.value)) || null
    : null
)
function handleExamCategoryFilterChange() {
  selectedDirectionId.value = ''
  targetFilterTouched.value = true
}
function handleRegionFilterChange() {
  selectedDirectionId.value = ''
  targetFilterTouched.value = true
}
function handleDirectionFilterChange() {
  targetFilterTouched.value = true
}
const targetFilterTouched = ref(false)
function applyDefaultTargetFilters(force = false) {
  if (targetFilterTouched.value && !force) return
  const preferredCategory = findCategoryByPreference(userStore.preferences?.examCategory)
  selectedExamCategoryId.value = preferredCategory?.id || ''
  const preferredProvince = normalizeProvinceCode(userStore.selectedProvince || '')
  if (preferredProvince && preferredProvince !== 'all') {
    selectedRegionId.value = regionOptions.value.find((region) => region.province === preferredProvince)?.id || ''
  } else {
    selectedRegionId.value = ''
  }
  selectedDirectionId.value = ''
}

// Build target filter params for API calls
const targetFilterParams = computed(() => {
  const params = {}
  const cat = selectedCategoryNode.value
  const region = selectedRegionNode.value
  const dir = selectedDirectionNode.value
  if (cat) {
    params.examCategory = cat.examCategory || cat.name
  }
  if (region) {
    if (region.province) params.province = region.province
  }
  if (dir) {
    if (dir.examSubcategory) params.examSubcategory = dir.examSubcategory
    if (dir.subcategory) params.subcategory = dir.subcategory
    if (dir.subcategory2) params.subcategory2 = dir.subcategory2
    if (!dir.subcategory && !dir.subcategory2) params.subcategory2 = dir.name
    if (dir.position) params.position = dir.position
    if (dir.province) params.province = dir.province
  }
  if (examMode.value !== 'fullExam' && selectedYearsFilter.value.length) {
    params.year = selectedYearsFilter.value.join(',')
  }
  return params
})

watch(isFixedPracticeEntry, (fixed) => {
  if (fixed) {
    examMode.value = 'free'
    questionCount.value = 1
    dimensionFilters.value = [RANDOM_DIMENSION_KEY]
  }
}, { immediate: true })

watch(fullExamSuiteOptions, (suites) => {
  if (!suites.length) {
    selectedFullExamSuiteId.value = ''
    return
  }
  if (!suites.some((suite) => suite.id === selectedFullExamSuiteId.value)) {
    selectedFullExamSuiteId.value = suites[0].id
  }
}, { immediate: true })

watch(() => [userStore.selectedProvince, userStore.preferences?.examCategory], () => {
  applyDefaultTargetFilters()
  refreshFullExamSuites().catch(() => null)
}, { immediate: true })

watch(targetFilterParams, () => {
  refreshFullExamSuites().catch(() => null)
}, { deep: true })

watch(() => userStore.preferences?.preferredQuestionDimensions, () => {
  applyPreferredQuestionDimensions()
}, { immediate: true, deep: true })

function handleDimensionFiltersChange(values = []) {
  questionTypeTouched.value = true
  const selected = Array.isArray(values) ? values.filter(Boolean) : []
  const specific = selected.filter((item) => item !== RANDOM_DIMENSION_KEY)
  dimensionFilters.value = specific.length ? specific : [RANDOM_DIMENSION_KEY]
}

function applyPreferredQuestionDimensions() {
  if (questionTypeTouched.value || !showPracticeConfig.value) return
  const validKeys = new Set(questionCategoryOptions.map((item) => item.key).filter((item) => item && item !== RANDOM_DIMENSION_KEY))
  const preferred = Array.isArray(userStore.preferences?.preferredQuestionDimensions)
    ? userStore.preferences.preferredQuestionDimensions
      .map((item) => String(item || '').trim())
      .filter((item, index, list) => validKeys.has(item) && list.indexOf(item) === index)
    : []
  dimensionFilters.value = preferred.length ? preferred : [RANDOM_DIMENSION_KEY]
}

function applyUserPracticePreferencesToQuestions(questions = []) {
  const prefs = userStore.preferences || {}
  const target = source.value === 'targeted' ? (targetedStore.selectionPayload || {}) : {}
  let targetPrepTime = Number(target.prepTime || 0)
  let targetAnswerTime = Number(target.answerTime || 0)

  // Fallback: parse timingMode/interviewFormat when prepTime/answerTime not explicitly set
  if (targetPrepTime === 0 && targetAnswerTime === 0) {
    const parsed = parseTimingFormat(target.timingMode || target.interviewFormat || '')
    if (parsed) {
      targetPrepTime = parsed.prepTime
      targetAnswerTime = parsed.answerTime
    }
  }

  const prepTime = Number(prefs.defaultPrepTime || 0)
  const answerTime = Number(prefs.defaultAnswerTime || 0)
  return questions.map((question) => ({
    ...question,
    prepTime: targetPrepTime || prepTime || Number(question?.prepTime || 90),
    answerTime: targetAnswerTime || answerTime || Number(question?.answerTime || 180),
    timingMode: target.timingMode || question?.timingMode || '',
    interviewFormat: target.interviewFormat || question?.interviewFormat || ''
  }))
}

function applyFullExamTimingMode(questions = []) {
  if (examMode.value !== 'fullExam') return questions
  const suiteProvince = selectedFullExamSuite.value?.province || userStore.selectedProvince
  return questions.map((question) => ({
    ...question,
    fullExamTimingMode: question?.fullExamTimingMode || (suiteProvince === 'jiangsu' ? JIANGSU_FULL_EXAM_TIMING_MODE : '')
  }))
}

async function refreshFullExamSuites() {
  if (!hasFullAccess.value) {
    fullExamSuites.value = []
    selectedFullExamSuiteId.value = ''
    fullExamSuitesLoading.value = false
    return
  }
  fullExamSuitesLoading.value = true
  try {
    const filters = targetFilterParams.value
    const suites = await fetchFullExamSuites(
      getQuestions,
      filters.province || userStore.selectedProvince,
      { params: filters }
    )
    fullExamSuites.value = suites
  } catch (error) {
    fullExamSuites.value = []
    message.warning(error?.message || '真题套卷加载失败，请稍后重试。')
  } finally {
    fullExamSuitesLoading.value = false
  }
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
  userStore.loadUserInfo().catch(() => null)
  refreshFullExamSuites().catch(() => null)
  loadAsrStatus().catch(() => null)
  doPermissionCheck()
})

onUnmounted(() => {
  clearInterval(countdownTimer)
  clearInterval(waitTimer)
  if (!examStore.mediaStream) {
    recorder.destroyStream()
  }
  if (testBlobUrl.value) {
    URL.revokeObjectURL(testBlobUrl.value)
  }
})

async function doPermissionCheck() {
  currentStep.value = 0
  permissionError.value = ''
  const permissionStream = await checkBoth({ keepStream: true })
  if (permissionStream) {
    videoEnabled.value = true
    currentStep.value = 1
    recorder.setStream(permissionStream)
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
  if (!recorder.stream.value) {
    await recorder.initStream({ videoEnabled: videoEnabled.value })
  }
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

async function enterExam() {
  if (enteringExam.value) return

  await loadAsrStatus().catch(() => null)
  if (asrUnavailable.value) {
    message.warning('语音转写服务未就绪，请稍后重试。')
    return
  }

  enteringExam.value = true
  let questions = []
  const recommendedId = String(route.query.questionId || '')
  const freeQuestionCount = Math.max(1, Math.min(10, Number(questionCount.value) || DEFAULT_EXAM_QUESTION_COUNT))
  const targetQuestionCount = isTrialEntry.value
    ? 1
    : examMode.value === 'fullExam'
      ? (selectedFullExamSuite.value?.questions?.length || 0)
      : freeQuestionCount

  try {
    if (!isTrialEntry.value && !hasFullAccess.value) {
      billingStore.openPaywall(route.fullPath, examMode.value === 'fullExam' ? '全真模拟' : '专项练习')
      router.push('/')
      return
    }

    if (isTrialEntry.value) {
      try {
        const trialQuestion = await getQuestionById(billingStore.trialQuestion.id)
        questions = trialQuestion ? [trialQuestion] : []
      } catch {
        const fallbackQuestion = await getQuestionById('q001')
        questions = fallbackQuestion ? [fallbackQuestion] : []
      }
    } else if (source.value === 'targeted' && targetedStore.generatedQuestions.length) {
      questions = await ensureScoringReadyQuestions(targetedStore.generatedQuestions, {
        allowAutoSupplement: false
      })
    } else if (source.value === 'targeted' && recommendedId) {
      try {
        const cached = sessionStorage.getItem('targeted_question')
        const selectedQuestion = cached ? JSON.parse(cached) : await getQuestionById(recommendedId)
        questions = await ensureScoringReadyQuestions([selectedQuestion], {
          allowAutoSupplement: false
        })
      } catch {
        questions = await fetchScoringReadyRandomQuestions(targetQuestionCount, { params: targetFilterParams.value })
      }
    } else if (source.value === 'training' && recommendedId) {
      try {
        const cached = sessionStorage.getItem('training_question')
        const selectedQuestion = cached ? JSON.parse(cached) : await getQuestionById(recommendedId)
        questions = await ensureScoringReadyQuestions([selectedQuestion], {
          allowAutoSupplement: false
        })
      } catch {
        questions = await fetchScoringReadyRandomQuestions(targetQuestionCount, { params: targetFilterParams.value })
      }
    } else if (recommendedId) {
      try {
        const question = await getQuestionById(recommendedId)
        questions = await ensureScoringReadyQuestions([question], { requiredCount: 1 })
      } catch {
        questions = await fetchScoringReadyRandomQuestions(targetQuestionCount, { params: targetFilterParams.value })
      }
    } else if (examMode.value === 'fullExam') {
      if (!selectedFullExamSuite.value) {
        message.warning('当前省份暂无整套真题套卷，请切换江苏、安徽或湖南。')
        return
      }
      questions = await loadFullExamSuiteQuestions(selectedFullExamSuite.value, getQuestionById)
      questions = await ensureScoringReadyQuestions(questions, {
        requiredCount: selectedFullExamSuite.value.questions.length,
        allowAutoSupplement: false
      })
    } else {
      questions = await fetchScoringReadyRandomQuestions(targetQuestionCount, { params: targetFilterParams.value })
    }

    if (!questions.length) {
      userStore.requireProvinceSelection(true)
      message.warning('当前省份暂无可用题目，请先重新选择省份。')
      return
    }

    if (examMode.value === 'fullExam' && selectedFullExamSuite.value && questions.length !== selectedFullExamSuite.value.questions.length) {
      message.warning('当前套题题目加载不完整，请切换其他套卷后重试。')
      return
    }

    questions = applyFullExamTimingMode(applyUserPracticePreferencesToQuestions(questions))

    examStore.storeStream(recorder.stream.value)
    examStore.setVideoEnabled(videoEnabled.value)

    if (examMode.value === 'fullExam') {
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
          await startFullExam(pendingQuestions)
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
  await startFullExam(pendingQuestions)
}

function exitWaitingRoom() {
  clearInterval(waitTimer)
  pendingQuestions = []
  waitingRoom.value = false
  enteringExam.value = false
  router.push('/')
}

async function startFullExam(questions) {
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

.fixed-practice-mode {
  display: flex;
  align-items: center;
  gap: 10px;
  min-height: 48px;
  padding: 10px 12px;
  border: 1px solid rgba(27, 95, 170, 0.14);
  border-radius: 12px;
  background: rgba(27, 95, 170, 0.06);
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

.practice-config__meta {
  color: @text-secondary;
  font-size: @font-size-xs;
  line-height: 1.6;
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

.waiting-room__actions {
  justify-content: center;
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
