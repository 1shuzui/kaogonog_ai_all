<!--
小程序考试准备页，负责展示本次练习/全真模拟的题量、时间规则、媒体检查和进入考场按钮。

准备页只做进入考场前的确认，不展示题目分数或评分反馈。全真模拟应优先按真实套题组织，时间模式来自题库元数据或定向分类规则。
点击进入前需要登录和权益可用，避免到考场后才被拦住。

@param: 无；准备信息来自 exam store、路由参数和权益状态。
@return: 渲染考试说明、媒体检查、权益提示和进入考场入口。
@raises: 不主动抛业务异常；无权益、抽题失败或媒体权限异常由页面提示承接。
-->
<template>
  <view class="motion-page page learner-page learner-prepare" :class="motionClass" :style="motionStyle">
    <BackgroundAnswers />
    <view class="learner-kicker"><LearnerIcon name="audio" :size="24" /><text>{{ pageTitle }}</text></view>
    <text class="page-title">这次，怎么练？</text>
    <text class="page-desc">{{ practiceSummary }} · 提交后可继续下一题</text>
    <view v-if="selection.ids.length" class="card"><text class="section-title">已选 {{ selection.ids.length }} 道题，将按原顺序作答</text><text class="page-desc">{{ inheritedSummary }}</text></view>
    <view v-if="entryError" class="card"><text class="page-desc">{{ entryError }}。原选择已保留，可再次点击进入考场重试。</text></view>

    <view v-if="readonlyMode" class="card access-card">
      <text class="access-card__title">未开通正式训练</text>
      <text class="access-card__desc">可以先体验 1 道试用题，或开通套餐后进入全真模拟、专项练习和训练复盘。</text>
      <view class="access-card__actions">
        <button class="secondary-button" :disabled="loading || accessLoading" @tap="startTrialEntry">试用 1 题</button>
        <button class="primary-button" :disabled="loading || accessLoading" @tap="goPricing">开通套餐</button>
      </view>
    </view>

    <view v-if="asrUnavailable" class="card service-card">
      <text class="service-card__title">语音转写服务未就绪</text>
      <text class="service-card__desc">{{ asrStatusText }}</text>
    </view>

    <view class="card">
      <view class="section-head">
        <text class="section-title">{{ fixedPracticeEntry ? '专项练习配置' : '选择练习模式' }}</text>
      </view>
      <view v-if="fixedPracticeEntry" class="fixed-practice-mode">
        <text class="fixed-practice-mode__title">专项练习</text>
        <text class="fixed-practice-mode__desc">已使用当前生成题目进入练习</text>
      </view>

      <view v-else class="mode-grid">
        <view class="mode-card" :class="{ 'mode-card--active': mode === 'free' }" @tap.stop="selectFreeMode">
          <LearnerIcon name="aim" /><text class="mode-card__title">专项练习</text>
          <text class="mode-card__desc">适合专项训练和即时复盘</text>
        </view>
        <view class="mode-card" :class="{ 'mode-card--active': mode === 'fullExam' }" @tap.stop="selectFullExamMode">
          <LearnerIcon name="read" /><text class="mode-card__title">全真模拟</text>
          <text class="mode-card__desc">按真题套卷连续作答</text>
        </view>
      </view>

      <view v-if="showPracticeConfig" class="config-row">
        <text>题目数量</text>
        <view class="stepper">
          <button class="stepper__button" :disabled="count <= 1" aria-label="减少题目数量" @tap="decreaseCount">−</button>
          <text class="stepper__value">{{ count }}</text>
          <button class="stepper__button" :disabled="trial || count >= MAX_FREE_QUESTION_COUNT" aria-label="增加题目数量" @tap="increaseCount">+</button>
        </view>
      </view>

      <MotionCollapse v-if="!fixedPracticeEntry" class="prepare-advanced" :open="advancedOpen" title="题目范围与题型" :revision="[mode, fullExamSuites, hasDirectionOptions]" @toggle="advancedOpen = !advancedOpen">
      <text class="ui-helper">{{ mode === 'fullExam' ? '全真模拟按完整真题套卷练习，保留套卷时间规则。' : '可选，不修改也能直接开始。' }}</text>
      <LightSelector title="考试大类" :options="examCategoryNames" :value="examCategoryIndex" @change="onExamCategoryFilterChange">
        <view class="config-row">
          <text>考试大类</text>
          <text class="config-row__value">{{ selectedExamCategoryName }}</text>
        </view>
      </LightSelector>
      <LightSelector title="地区" :options="regionNames" :value="regionIndex" :disabled="!regionOptions.length" @change="onRegionFilterChange">
        <view class="config-row">
          <text>地区</text>
          <text class="config-row__value">{{ selectedRegionNameText }}</text>
        </view>
      </LightSelector>
      <LightSelector v-if="hasDirectionOptions" title="方向" :options="directionNames" :value="directionIndex" @change="onDirectionFilterChange">
        <view class="config-row">
          <text>方向</text>
          <text class="config-row__value">{{ selectedDirectionNameText }}</text>
        </view>
      </LightSelector>

      <view v-if="mode === 'fullExam'" class="suite-panel">
        <view class="config-row config-row--suite">
          <text>真题套卷（{{ fullExamSuiteOptions.length }} 套）</text>
          <text class="config-row__value">{{ selectedFullExamSuiteLabel }}</text>
        </view>
        <picker
          v-if="fullExamSuiteOptions.length"
          mode="selector"
          :range="fullExamPickerOptions"
          range-key="label"
          :value="selectedFullExamSuiteIndex"
          @change="onFullExamSuiteChange"
        >
          <view class="suite-picker">
            <text>{{ selectedFullExamSuite?.title || '选择整套真题' }}</text>
            <text class="suite-picker__arrow">点击选卷</text>
          </view>
        </picker>
        <text v-if="selectedFullExamSuite" class="suite-panel__summary">{{ selectedFullExamSuiteSummary }}</text>
        <text v-else class="suite-panel__summary">{{ fullExamSuitesLoading ? '正在加载真题套卷...' : '当前筛选范围暂无完整真题套卷，请调整地区或分类。' }}</text>
        <text v-if="fullExamSuiteOptions.length === 1" class="page-desc">当前筛选范围收录 1 套完整真题套卷，可调整地区或分类查看其他题源。</text>
      </view>

      <view v-if="mode !== 'fullExam'" class="config-row config-row--year" @tap="showYearPicker = true">
        <text>年份</text>
        <text class="config-row__value">{{ yearLabel }}</text>
      </view>

      <LearnerSheet class="prepare-year-sheet" :show="showYearPicker" title="选择年份" :body-height="yearOptions.length * 52 + 56" @close="showYearPicker = false">
          <text class="ui-helper">{{ !hasFullAccess ? '开通题库后可查看实际收录年份；试用题由系统提供。' : filterMetadata.loading.value ? '正在读取题库年份…' : '仅列出当前地区 / 方向题库已收录的年份，可多选。' }}</text>
          <view v-if="filterMetadata.error.value"><text class="ui-error">{{ filterMetadata.error.value }}</text><button class="ui-link" @tap="refreshFilterMetadata">重新加载</button></view>
          <text v-else-if="hasFullAccess && !filterMetadata.loading.value && !yearOptions.length" class="ui-helper">当前范围暂无可用年份，可保留不限年份或调整范围。</text>
          <button v-if="selectedYearsFilter.length" class="ui-link" @tap="selectedYearsFilter = []">清除年份条件</button>
          <checkbox-group @change="onYearFilterChange">
            <label v-for="opt in yearOptions" :key="opt.value" class="year-checkbox">
              <checkbox :value="opt.value" :checked="opt.checked" />
              <text>{{ opt.value }}</text>
            </label>
          </checkbox-group>
      </LearnerSheet>

      <view v-if="showPracticeConfig" class="question-type-panel">
        <view class="config-row config-row--type">
          <text>题目类型</text>
          <text class="config-row__value">{{ selectedCategoryName }}</text>
        </view>
        <view class="type-chip-grid">
          <view
            v-for="item in questionCategoryOptions"
            :key="item.key"
            class="type-chip"
            :class="{
              'type-chip--active': isTypeSelected(item.key),
              'type-chip--disabled': item.key === RANDOM_DIMENSION_KEY && selectedSpecificDimensions.length > 0
            }"
            @tap="toggleQuestionType(item.key)"
          >
            <text>{{ item.name }}</text>
          </view>
        </view>
      </view>
      </MotionCollapse>
    </view>

    <view class="card learner-media-card">
      <view class="section-head"><text class="section-title">录制方式</text></view>
      <MotionSegmented class="prepare-media-options" :model-value="mediaMode" :options="mediaOptions" @change="value => value === 'audio' ? selectAudioMode() : selectVideoMode()" />
      <view class="learner-kicker"><LearnerIcon :name="mediaMode === 'audio' ? 'audio' : 'video-camera'" :size="22" /><text>{{ mediaMode === 'audio' ? '只关注声音和表达' : '同步记录声音和画面' }}</text></view>
    </view>

    <view class="card tips-card">
      <text class="tips-card__title">开考前检查</text>
      <text class="tips-card__line">保持环境安静，进入考场后请授权麦克风；录像模式还需授权摄像头。</text>
      <text class="tips-card__line">{{ pageDesc }}</text>
      <text class="tips-card__line">提交后上传和点评在后台处理，可继续下一题。</text>
    </view>

    <view v-if="!readonlyMode" class="prepare-action-bar">
    <view class="prepare-action-summary"><text>{{ practiceSummary }}</text><text>{{ mediaMode === 'audio' ? '仅录音' : '录像＋录音' }}</text></view>
    <button
      v-if="!readonlyMode"
      class="primary-button"
      :class="{ 'motion-shimmer': loading || accessLoading || enteringExam }"
      :disabled="loading || accessLoading || enteringExam || asrUnavailable"
      :loading="loading"
      @tap="startPractice"
    >
      {{ asrUnavailable ? '语音服务未就绪' : loading || enteringExam ? '正在准备考场…' : '进入考场' }}
    </button>
    </view>
  </view>
</template>

<script setup>
import MotionSegmented from '../../components/MotionSegmented.vue'
const mediaOptions = [{ value: 'audio', label: '仅录音' }, { value: 'video', label: '录像＋录音' }]
import { usePageMotion } from '../../motion/useMotion'
const { motionClass, motionStyle } = usePageMotion()
import LearnerIcon from '../../components/LearnerIcon.vue'
import BackgroundAnswers from '../../components/BackgroundAnswers.vue'
import { computed, ref, watch } from 'vue'
import { onLoad, onShow, onUnload } from '@dcloudio/uni-app'
import LightSelector from '../../components/LightSelector.vue'
import LearnerSheet from '../../components/LearnerSheet.vue'
import MotionCollapse from '../../components/MotionCollapse.vue'
import { useExamStore } from '../../stores/exam'
import { useBillingStore } from '../../stores/billing'
import { useQuestionBankStore } from '../../stores/questionBank'
import { useSubscriptionStore } from '../../stores/subscription'
import { useUserStore } from '../../stores/user'
import { useTargetedStore } from '../../stores/targeted'
import { readPracticeSelection, loadSelectedQuestions, practiceModeFor, practiceFilterSummary } from '../../../../shared/practiceSelection.mjs'
import { getQuestionById, getQuestions } from '../../api/questionBank'
import {
  getFullExamSuiteQuestions as requestFullExamSuiteQuestions,
  getFullExamSuites as requestFullExamSuites
} from '../../api/exam'
import { getAsrStatus } from '../../api/scoring'
import { getTrialQuestion, getTrialStatus } from '../../api/trial'
import { hasPremiumAccess } from '../../utils/access'
import { hideLoading, requireLogin, showLoading, toast } from '../../utils/navigation'
import { QUESTION_CATEGORIES } from '../../utils/constants'
import { useQuestionFilters } from '../../utils/useQuestionFilters'
import {
  fetchFullExamSuites,
  getFullExamSuiteSummary,
  loadFullExamSuiteQuestions,
  normalizeProvinceCode
} from '../../utils/fullExamSuites'
import { DEFAULT_TARGETED_POSITION_TREE } from '../../utils/targetedOptions'

const examStore = useExamStore()
const billingStore = useBillingStore()
const questionBankStore = useQuestionBankStore()
const filterMetadata = useQuestionFilters()
const subscriptionStore = useSubscriptionStore()
const userStore = useUserStore()
const targetedStore = useTargetedStore()
const selection = ref({ ids: [], filters: {} })
const entryError = ref('')
const selectionError = ref('')
const DEFAULT_EXAM_QUESTION_COUNT = 5
const JIANGSU_FULL_EXAM_TIMING_MODE = 'jiangsu_5_15'
const MAX_FREE_QUESTION_COUNT = 10
const STATE_REFRESH_TIMEOUT_MS = 6000
const ENTRY_STATE_REFRESH_TIMEOUT_MS = 2500
const ENTRY_ASR_STATUS_TIMEOUT_MS = 1500
const ENTER_ROOM_TIMEOUT_MS = 10000
const ACCESS_STATE_CACHE_MS = 30000
const ASR_STATUS_CACHE_MS = 30000
const count = ref(DEFAULT_EXAM_QUESTION_COUNT)
const advancedOpen = ref(false)
const mode = ref('free')
watch(mode, value => { if (value === 'fullExam') advancedOpen.value = true })
const mediaMode = ref('audio')
const selectedDimensions = ref(['random'])
const questionTypeTouched = ref(false)
// Targeted filter state
const selectedExamCategoryId = ref('')
const selectedRegionId = ref('')
const selectedDirectionId = ref('')
const selectedYearsFilter = ref([])
const targetFilterTouched = ref(false)
const showYearPicker = ref(false)
const selectedFullExamSuiteId = ref('')
const fullExamSuites = ref([])
let fullExamSuitesRequest = 0
onUnload(() => { fullExamSuitesRequest += 1 })
const fullExamSuitesLoading = ref(false)
const loading = ref(false)
const accessLoading = ref(false)
const enteringExam = ref(false)
const source = ref('')
const trial = ref(false)
const trialStatus = ref(null)
const asrStatus = ref(null)
const recommendedQuestionId = ref('')
let accessRefreshedAt = 0
let asrStatusRefreshedAt = 0
let accessRefreshPromise = null
let asrStatusRefreshPromise = null
const hasFullAccess = computed(() => hasPremiumAccess(userStore, billingStore, subscriptionStore))
const readonlyMode = computed(() => !trial.value && !hasFullAccess.value)
const asrUnavailable = computed(() => asrStatus.value && asrStatus.value.ready === false)
const asrStatusText = computed(() => {
  if (!asrStatus.value) return ''
  return asrStatus.value.message || '请稍后重试，或联系管理员检查后端 Whisper/ffmpeg 配置。'
})
const RANDOM_DIMENSION_KEY = 'random'
const questionCategoryOptions = [
  { key: RANDOM_DIMENSION_KEY, name: '随机题型' },
  ...QUESTION_CATEGORIES.filter((item) => item.key)
]
const fixedPracticeSources = new Set(['targeted', 'training', 'jiangsu', 'bank', 'favorites'])
const fixedPracticeEntry = computed(() => fixedPracticeSources.has(source.value) || selection.value.ids.length > 0)
const inheritedSummary = computed(() => practiceFilterSummary(selection.value.filters, userStore.provinces, QUESTION_CATEGORIES))
const showPracticeConfig = computed(() => mode.value === 'free' && !fixedPracticeEntry.value)
const selectedSpecificDimensions = computed(() => selectedDimensions.value.filter((item) => item && item !== RANDOM_DIMENSION_KEY))
const selectedDimensionParam = computed(() => selectedSpecificDimensions.value.join(','))
const fullExamSuiteOptions = computed(() => fullExamSuites.value)
const selectedFullExamSuite = computed(() => (
  fullExamSuiteOptions.value.find((suite) => suite.id === selectedFullExamSuiteId.value)
  || fullExamSuiteOptions.value[0]
  || null
))
const selectedFullExamSuiteIndex = computed(() => Math.max(0, fullExamSuiteOptions.value.findIndex((suite) => suite.id === selectedFullExamSuite.value?.id)))
const fullExamPickerOptions = computed(() => fullExamSuiteOptions.value.map((suite) => ({
  id: suite.id,
  label: suite.title
})))
const selectedFullExamSuiteLabel = computed(() => selectedFullExamSuite.value?.title || '暂无套题')
const selectedFullExamSuiteSummary = computed(() => getFullExamSuiteSummary(selectedFullExamSuite.value))
const practiceSummary = computed(() => trial.value ? '1 道试用题' : mode.value === 'fullExam'
  ? `全真模拟 · ${selectedFullExamSuite.value?.questionCount || '待选'} 题`
  : `${selection.value.ids.length || count.value} 道题 · ${selectedCategoryName.value}`)
const pageTitle = computed(() => (mode.value === 'fullExam' ? '全真模拟准备' : '专项练习准备'))
const pageDesc = computed(() => (
  mode.value === 'fullExam'
    ? '按照整套真题连续作答，提交后自动转写并评分。'
    : '按题型进行专项训练，支持录音和录像作答，提交后自动转写并评分。'
))
const selectedCategoryName = computed(() => {
  if (!selectedSpecificDimensions.value.length) return '随机题型'
  const names = selectedSpecificDimensions.value
    .map((key) => questionCategoryOptions.find((item) => item.key === key)?.name)
    .filter(Boolean)
  return names.join('、') || '随机题型'
})

watch(pageTitle, (title) => {
  if (typeof uni.setNavigationBarTitle === 'function') {
    uni.setNavigationBarTitle({ title })
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

watch(() => userStore.preferences?.preferredQuestionDimensions, () => {
  applyPreferredQuestionDimensions()
}, { immediate: true, deep: true })

// Targeted filter computed properties
const examCategoryOptions = DEFAULT_TARGETED_POSITION_TREE
const examCategoryNames = computed(() => ['不限', ...examCategoryOptions.map(c => c.name)])
const examCategoryIndex = computed(() => {
  const idx = examCategoryOptions.findIndex(c => String(c.id) === String(selectedExamCategoryId.value))
  return idx >= 0 ? idx + 1 : 0
})
const selectedExamCategoryName = computed(() => {
  const cat = examCategoryOptions.find(c => String(c.id) === String(selectedExamCategoryId.value))
  return cat ? cat.name : '不限'
})
const selectedCategoryNode = computed(() =>
  selectedExamCategoryId.value
    ? examCategoryOptions.find(c => String(c.id) === String(selectedExamCategoryId.value)) || null
    : null
)
function uniqueRegionsFromTree() {
  const seen = new Set()
  const regions = []
  examCategoryOptions.forEach((category) => {
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
const regionNames = computed(() => ['不限', ...regionOptions.value.map(r => r.name)])
const regionIndex = computed(() => {
  const idx = regionOptions.value.findIndex(r => String(r.id) === String(selectedRegionId.value))
  return idx >= 0 ? idx + 1 : 0
})
const selectedRegionNameText = computed(() => {
  const r = regionOptions.value.find(r => String(r.id) === String(selectedRegionId.value))
  return r ? r.name : '不限'
})
const selectedRegionNode = computed(() =>
  selectedRegionId.value
    ? regionOptions.value.find(r => String(r.id) === String(selectedRegionId.value)) || null
    : null
)
function findCategoryByPreference(value = '') {
  const text = String(value || '').trim()
  if (!text) return null
  return examCategoryOptions.find((category) => (
    String(category.id) === text
    || String(category.name) === text
    || String(category.examCategory || '') === text
  )) || null
}
function matchingTreeRegions() {
  const region = selectedRegionNode.value
  if (!region) return []
  const categories = selectedCategoryNode.value ? [selectedCategoryNode.value] : examCategoryOptions
  return categories.flatMap((category) => (
    (category.children || []).filter((item) => normalizeProvinceCode(item.province || '') === region.province)
  ))
}
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
const hasDirectionOptions = computed(() => directionOptions.value.length > 0)
const directionNames = computed(() => ['不限', ...directionOptions.value.map(d => d.name)])
const directionIndex = computed(() => {
  const idx = directionOptions.value.findIndex(d => String(d.id) === String(selectedDirectionId.value))
  return idx >= 0 ? idx + 1 : 0
})
const selectedDirectionNameText = computed(() => {
  const d = directionOptions.value.find(d => String(d.id) === String(selectedDirectionId.value))
  return d ? d.name : '不限'
})
const selectedDirectionNode = computed(() =>
  selectedDirectionId.value
    ? directionOptions.value.find(d => String(d.id) === String(selectedDirectionId.value)) || null
    : null
)
const yearOptions = computed(() =>
  filterMetadata.options.value.year.map(y => ({ value: y, checked: selectedYearsFilter.value.includes(y) }))
)
const yearLabel = computed(() =>
  selectedYearsFilter.value.length ? selectedYearsFilter.value.join('、') : '不限年份（可多选）'
)

// Build target filter params for API calls
const targetFilterParams = computed(() => {
  if (fixedPracticeEntry.value) return selection.value.filters
  const params = {}
  const cat = selectedCategoryNode.value
  const region = selectedRegionNode.value
  const dir = selectedDirectionNode.value
  if (cat) params.examCategory = cat.examCategory || cat.name
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
  if (mode.value !== 'fullExam' && selectedYearsFilter.value.length) params.year = selectedYearsFilter.value.join(',')
  return params
})

// Use the same effective scope as fetchRandom; keep its province fallback and
// exact dimension parameter, but exclude the year facet's own selection.
const metadataFilterParams = computed(() => ({
  province: targetFilterParams.value.province || userStore.selectedProvince,
  dimension: selectedDimensionParam.value,
  ...targetFilterParams.value,
  year: ''
}))
function refreshFilterMetadata() {
  return filterMetadata.refresh(metadataFilterParams.value, hasFullAccess.value && userStore.isAuthenticated)
}
// Do not request on every checkbox change: a facet excludes its own year filter.
watch(() => JSON.stringify({ ...metadataFilterParams.value, access: hasFullAccess.value && userStore.isAuthenticated }), refreshFilterMetadata, { immediate: true })

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

watch(() => [userStore.selectedProvince, userStore.preferences?.examCategory], () => {
  applyDefaultTargetFilters()
  refreshFullExamSuites().catch(() => null)
}, { immediate: true })

watch(targetFilterParams, () => {
  refreshFullExamSuites().catch(() => null)
}, { deep: true })

function onExamCategoryFilterChange(e) {
  targetFilterTouched.value = true
  const idx = Number(e.detail.value)
  if (idx === 0) {
    selectedExamCategoryId.value = ''
  } else {
    const cat = examCategoryOptions[idx - 1]
    selectedExamCategoryId.value = cat ? cat.id : ''
  }
  selectedDirectionId.value = ''
}
function onRegionFilterChange(e) {
  targetFilterTouched.value = true
  const idx = Number(e.detail.value)
  if (idx === 0) {
    selectedRegionId.value = ''
  } else {
    const r = regionOptions.value[idx - 1]
    selectedRegionId.value = r ? r.id : ''
  }
  selectedDirectionId.value = ''
}
function onDirectionFilterChange(e) {
  targetFilterTouched.value = true
  const idx = Number(e.detail.value)
  if (idx === 0) {
    selectedDirectionId.value = ''
  } else {
    const d = directionOptions.value[idx - 1]
    selectedDirectionId.value = d ? d.id : ''
  }
}
function onYearFilterChange(e) {
  selectedYearsFilter.value = e.detail.value || []
}

function applyUserPracticePreferencesToQuestions(questions = []) {
  const prefs = userStore.preferences || {}
  const prefPrepTime = Number(prefs.defaultPrepTime || 0)
  const prefAnswerTime = Number(prefs.defaultAnswerTime || 0)
  return questions.map((question) => ({
    ...question,
    prepTime: Number(question?.prepTime) || prefPrepTime || 90,
    answerTime: Number(question?.answerTime) || prefAnswerTime || 180,
    timingMode: question?.timingMode || ''
  }))
}

function applyFullExamTimingMode(questions = []) {
  if (mode.value !== 'fullExam') return questions
  const suiteTiming = selectedFullExamSuite.value?.timingMode || ''
  const suiteProvince = selectedFullExamSuite.value?.province || userStore.selectedProvince
  return questions.map((question) => ({
    ...question,
    fullExamTimingMode: question?.timingMode || suiteTiming || (suiteProvince === 'jiangsu' ? JIANGSU_FULL_EXAM_TIMING_MODE : '')
  }))
}

async function refreshFullExamSuites() {
  const request = ++fullExamSuitesRequest
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
      {
        params: filters,
        getFullExamSuites: requestFullExamSuites
      }
    )
    if (request === fullExamSuitesRequest) fullExamSuites.value = suites
  } catch (error) {
    if (request !== fullExamSuitesRequest) return
    fullExamSuites.value = []
    toast(error?.message || '真题套卷加载失败，请稍后重试')
  } finally {
    if (request === fullExamSuitesRequest) fullExamSuitesLoading.value = false
  }
}

onLoad((query) => {
  source.value = String(query?.source || '')
  try { selection.value = readPracticeSelection(query, source.value === 'targeted' ? targetedStore.generatedQuestions : []) }
  catch (error) { selectionError.value = entryError.value = error.message }
  recommendedQuestionId.value = String(query?.questionId || '').trim()
  if (fixedPracticeEntry.value) {
    mode.value = 'free'
    count.value = 1
    selectedDimensions.value = [RANDOM_DIMENSION_KEY]
  }
  if (String(query?.mode || '') === 'fullExam') {
    mode.value = 'fullExam'
  } else if (String(query?.mode || '') === 'free') {
    mode.value = 'free'
  }
  if (fixedPracticeEntry.value) {
    mode.value = 'free'
  }
  if (String(query?.media || '') === 'video') {
    mediaMode.value = 'video'
  } else if (String(query?.media || '') === 'audio') {
    mediaMode.value = 'audio'
  }
  const requestedTrial = String(query?.trial || '') === '1'
  trial.value = requestedTrial && !hasFullAccess.value
  if (trial.value) count.value = 1
})

watch(fixedPracticeEntry, (fixed) => {
  if (!fixed) return
  mode.value = 'free'
  count.value = 1
  selectedDimensions.value = [RANDOM_DIMENSION_KEY]
}, { immediate: true })

onShow(() => {
  loading.value = false
  accessLoading.value = false
  enteringExam.value = false
  hideLoading()
  refreshAccessState({ force: true })
    .then(() => refreshFullExamSuites())
    .catch(() => null)
  refreshAsrStatus().catch(() => null)
})

function withTimeout(promise, timeoutMs, fallback = null) {
  return new Promise((resolve) => {
    let settled = false
    const timer = setTimeout(() => {
      if (settled) return
      settled = true
      resolve(fallback)
    }, timeoutMs)

    Promise.resolve(promise)
      .then((value) => {
        if (settled) return
        settled = true
        clearTimeout(timer)
        resolve(value)
      })
      .catch(() => {
        if (settled) return
        settled = true
        clearTimeout(timer)
        resolve(fallback)
      })
  })
}

function isFresh(timestamp, maxAgeMs) {
  return timestamp > 0 && Date.now() - timestamp < maxAgeMs
}

async function refreshAccessState(options = {}) {
  if (!userStore.isAuthenticated) return false
  const timeoutMs = Number(options.timeout || STATE_REFRESH_TIMEOUT_MS)
  const freshMs = Number(options.freshMs || ACCESS_STATE_CACHE_MS)
  if (options.force !== true && isFresh(accessRefreshedAt, freshMs)) {
    return hasFullAccess.value
  }
  if (!accessRefreshPromise) {
    accessLoading.value = true
    accessRefreshPromise = (async () => {
      try {
        await Promise.allSettled([
          userStore.loadUserInfo(),
          subscriptionStore.refresh({ skipErrorHandler: true })
        ])
        if (hasFullAccess.value && trial.value) {
          trial.value = false
          count.value = DEFAULT_EXAM_QUESTION_COUNT
        }
        if (trial.value) {
          trialStatus.value = await withTimeout(
            getTrialStatus({ skipErrorHandler: true }),
            timeoutMs,
            null
          )
        }
        accessRefreshedAt = Date.now()
        return hasFullAccess.value
      } finally {
        accessLoading.value = false
        accessRefreshPromise = null
      }
    })()
  }
  const result = await withTimeout(accessRefreshPromise, timeoutMs, null)
  return result ?? hasFullAccess.value
}

async function refreshAsrStatus(options = {}) {
  if (!userStore.isAuthenticated) return
  const timeoutMs = Number(options.timeout || STATE_REFRESH_TIMEOUT_MS)
  const freshMs = Number(options.freshMs || ASR_STATUS_CACHE_MS)
  if (options.force !== true && isFresh(asrStatusRefreshedAt, freshMs)) {
    return asrStatus.value
  }
  if (!asrStatusRefreshPromise) {
    asrStatusRefreshPromise = getAsrStatus({ skipErrorHandler: true })
      .then((status) => {
        asrStatus.value = status
        return status
      })
      .catch(() => asrStatus.value)
      .finally(() => {
        asrStatusRefreshedAt = Date.now()
        asrStatusRefreshPromise = null
      })
  }
  asrStatus.value = await withTimeout(asrStatusRefreshPromise, timeoutMs, asrStatus.value)
  return asrStatus.value
}

function selectFreeMode() {
  mode.value = 'free'
  applyPreferredQuestionDimensions()
}

function selectFullExamMode() {
  if (fixedPracticeEntry.value) return
  mode.value = 'fullExam'
}

function applyPreferredQuestionDimensions() {
  if (questionTypeTouched.value || !showPracticeConfig.value) return
  const validKeys = new Set(questionCategoryOptions.map((item) => item.key).filter((item) => item && item !== RANDOM_DIMENSION_KEY))
  const preferred = Array.isArray(userStore.preferences?.preferredQuestionDimensions)
    ? userStore.preferences.preferredQuestionDimensions
      .map((item) => String(item || '').trim())
      .filter((item, index, list) => validKeys.has(item) && list.indexOf(item) === index)
    : []
  selectedDimensions.value = preferred.length ? preferred : [RANDOM_DIMENSION_KEY]
}

function onFullExamSuiteChange(event) {
  const index = Number(event?.detail?.value || 0)
  const suite = fullExamSuiteOptions.value[index]
  if (suite) selectedFullExamSuiteId.value = suite.id
}

function selectAudioMode() {
  mediaMode.value = 'audio'
}

function selectVideoMode() {
  mediaMode.value = 'video'
}

function decreaseCount() {
  count.value = Math.max(1, count.value - 1)
}

function increaseCount() {
  if (trial.value) return
  count.value = Math.min(MAX_FREE_QUESTION_COUNT, count.value + 1)
}

function isTypeSelected(key) {
  return selectedDimensions.value.includes(key)
}

function toggleQuestionType(key) {
  questionTypeTouched.value = true
  if (key === RANDOM_DIMENSION_KEY) {
    if (selectedSpecificDimensions.value.length) return
    selectedDimensions.value = [RANDOM_DIMENSION_KEY]
    return
  }

  const specific = selectedSpecificDimensions.value
  if (specific.includes(key)) {
    const next = specific.filter((item) => item !== key)
    selectedDimensions.value = next.length ? next : [RANDOM_DIMENSION_KEY]
    return
  }

  selectedDimensions.value = [...specific, key]
}

async function startPractice() {
  if (!requireLogin()) return
  if (loading.value || enteringExam.value) return
  enteringExam.value = true
  loading.value = true
  showLoading('检查考场')
  entryError.value = ''
  try {
    if (selectionError.value) throw new Error(selectionError.value)
    const accessFresh = isFresh(accessRefreshedAt, ENTRY_STATE_REFRESH_TIMEOUT_MS)
    const asrFresh = isFresh(asrStatusRefreshedAt, ENTRY_ASR_STATUS_TIMEOUT_MS)
    await Promise.allSettled([
      accessFresh ? Promise.resolve() : refreshAccessState({ timeout: ENTRY_STATE_REFRESH_TIMEOUT_MS }),
      asrFresh ? Promise.resolve() : refreshAsrStatus({ timeout: ENTRY_ASR_STATUS_TIMEOUT_MS })
    ])
    if (asrUnavailable.value) {
      toast('语音转写服务未就绪，请稍后重试')
      return
    }
    if (trial.value && trialStatus.value?.trialCompleted) {
      toast('试用已完成，请开通套餐后继续练习')
      return
    }
    if (readonlyMode.value) {
      toast('请先开通套餐后进入正式考场')
      return
    }

    showLoading('抽取题目')
    let questions = []
    if (trial.value) {
      try {
        const trialQuestion = await withTimeout(getTrialQuestion(), ENTER_ROOM_TIMEOUT_MS, null)
        if (trialQuestion?.id) {
          questions = [trialQuestion]
        } else {
          const fallbackQuestion = await withTimeout(getQuestionById('q001'), ENTER_ROOM_TIMEOUT_MS, null)
          questions = fallbackQuestion?.id ? [fallbackQuestion] : []
        }
      } catch {
        const fallbackQuestion = await withTimeout(getQuestionById('q001'), ENTER_ROOM_TIMEOUT_MS, null)
        questions = fallbackQuestion?.id ? [fallbackQuestion] : []
      }
    } else {
      if (!userStore.isAdmin) {
        const status = subscriptionStore.status
        const remainingDaily = Math.max(0, Number(status.remainingDailyMinutes || 0))
        if (!status.canUse || remainingDaily <= 0) {
          toast('当前套餐额度不足')
          return
        }
      }
      questions = await withTimeout(
        selection.value.ids.length
          ? loadSelectedQuestions(selection.value.ids, getQuestionById)
          : mode.value === 'fullExam'
          ? loadFullExamSuiteQuestions(selectedFullExamSuite.value, getQuestionById, {
            getFullExamSuiteQuestions: requestFullExamSuiteQuestions
          })
          : fixedPracticeEntry.value
            ? Promise.reject(new Error('未找到所选题目，请返回选题页重新确认'))
            : questionBankStore.fetchRandom({
              province: targetFilterParams.value.province || userStore.selectedProvince,
              count: count.value,
              dimension: selectedDimensionParam.value,
              ...targetFilterParams.value
            }),
        ENTER_ROOM_TIMEOUT_MS,
        []
      )
    }

    if (!questions.length) {
      if (selection.value.ids.length) throw new Error('所选题目读取超时或暂不可用，选择已保留，请重试')
      toast(trial.value ? '试用题暂不可用，请稍后重试' : mode.value === 'fullExam' ? '当前省份暂无整套真题套卷' : '当前筛选条件暂无题目')
      return
    }
    const expectedSuiteQuestionCount = Number(selectedFullExamSuite.value?.questionCount || selectedFullExamSuite.value?.questions?.length || 0)
    if (mode.value === 'fullExam' && selectedFullExamSuite.value && expectedSuiteQuestionCount && questions.length !== expectedSuiteQuestionCount) {
      toast('当前套题题目加载不完整，请切换其他套卷后重试')
      return
    }
    if (selection.value.ids.length && questions.length !== selection.value.ids.length) throw new Error('指定题目尚未完整读取，请重试')
    const targetCount = trial.value ? 1 : selection.value.ids.length || (mode.value === 'fullExam' ? questions.length : count.value)
    const preparedQuestions = applyFullExamTimingMode(applyUserPracticePreferencesToQuestions(questions.slice(0, targetCount)))
    examStore.setMediaMode(mediaMode.value)
    await examStore.startFromQuestions(preparedQuestions, practiceModeFor(source.value, mode.value, trial.value))
    uni.navigateTo({ url: '/pages/exam/room' })
  } catch (error) {
    entryError.value = error?.message || '进入考场失败'
  } finally {
    loading.value = false
    enteringExam.value = false
    hideLoading()
  }
}

function startTrialEntry() {
  if (!requireLogin()) return
  trial.value = true
  count.value = 1
  startPractice()
}

function goPricing() {
  uni.navigateTo({ url: '/pages/pricing/index' })
}
</script>

<style scoped>
.learner-prepare.page { padding-bottom:calc(148px + env(safe-area-inset-bottom)); }
.learner-prepare .page-title { font-size:44rpx; margin:12rpx 0; }
.learner-prepare .page-desc { font-size:28rpx; margin-bottom:24rpx; }
.prepare-advanced { display:block; margin-top:16px; border-top:1px solid var(--ui-border); padding-top:8px; }
.prepare-action-bar { position:fixed; left:0; right:0; bottom:0; z-index:800; padding:12px 20px calc(12px + env(safe-area-inset-bottom)); background:var(--ui-surface); border-top:1px solid var(--ui-border); box-shadow:0 -4px 18px #20304708; }
.prepare-action-summary { display:flex; justify-content:space-between; align-items:center; gap:12px; margin-bottom:8px; color:var(--ui-muted); font-size:14px; line-height:1.5; }
.prepare-action-summary > text:first-child { flex:1; }
.prepare-action-summary > text:last-child { flex:none; }
.prepare-action-bar .primary-button { width:100%; }
.config-row__value::after { content:'›'; margin-left:8px; color:var(--ui-muted); }
.learner-prepare .access-card__desc,.learner-prepare .service-card__desc,
.learner-prepare .suite-panel__summary,.learner-prepare .suite-picker__arrow,
.learner-prepare .mode-card__desc,.learner-prepare .fixed-practice-mode__desc,
.learner-prepare .tips-card__line { color:var(--ui-muted); font-size:14px; line-height:1.65; }
.learner-prepare .stepper__button { color:var(--ui-link); }
.learner-prepare .stepper__button[disabled] { color:var(--ui-muted); background:#f1f3f6; }
.access-card {
  border-color: #bfd7ef;
  background: #f4f9fe;
}

.access-card__title,
.access-card__desc,
.service-card__title,
.service-card__desc {
  display: block;
}

.access-card__title,
.service-card__title {
  color: var(--ui-text);
  font-size: 30rpx;
  font-weight: 800;
}

.access-card__desc,
.service-card__desc {
  margin-top: 10rpx;
  color: var(--ui-muted);
  font-size: 14px;
  line-height: 1.6;
}

.access-card__actions {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 16rpx;
  margin-top: 22rpx;
}

.service-card {
  border-color: #f2c46d;
  background: #fff8eb;
}

.config-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 18rpx 0;
  color: var(--ui-text);
  font-size: 28rpx;
  font-weight: 600;
}

.config-row__value {
  flex: 1;
  margin-left: 24rpx;
  color: var(--ui-link);
  font-weight: 700;
  text-align: right;
}

.config-row--type {
  padding-bottom: 10rpx;
  align-items: flex-start;
}

.config-row--suite {
  padding-bottom: 10rpx;
  align-items: flex-start;
}

.media-row {
  margin-top: 18rpx;
}

.suite-panel {
  margin-top: 16rpx;
  padding: 18rpx;
  border: 1rpx solid var(--ui-border);
  border-radius: 14rpx;
  background: #f8fbff;
}

.suite-picker {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 18rpx;
  min-height: 44px;
  padding: 0 18rpx;
  border: 1rpx solid #bfd7ef;
  border-radius: 12rpx;
  background: #ffffff;
  color: var(--ui-text);
  font-size: 14px;
  font-weight: 700;
}

.suite-picker__arrow {
  flex-shrink: 0;
  color: var(--ui-link);
  font-size: 14px;
}

.suite-panel__summary {
  display: block;
  margin-top: 12rpx;
  color: var(--ui-muted);
  font-size: 14px;
  line-height: 1.6;
}

.fixed-practice-mode {
  margin-top: 8rpx;
  padding: 18rpx;
  border: 1rpx solid #bfd7ef;
  border-radius: 14rpx;
  background: #f4f9fe;
}

.fixed-practice-mode__title,
.fixed-practice-mode__desc {
  display: block;
}

.fixed-practice-mode__title {
  color: var(--ui-text);
  font-size: 29rpx;
  font-weight: 800;
}

.fixed-practice-mode__desc {
  margin-top: 8rpx;
  color: var(--ui-muted);
  font-size: 14px;
}

.question-type-panel {
  margin-top: 10rpx;
}

.type-chip-grid {
  display: flex;
  flex-wrap: wrap;
  gap: 14rpx;
  padding-top: 6rpx;
}

.type-chip {
  min-height: 44px;
  display: flex;
  align-items: center;
  justify-content: center;
  min-width: 148rpx;
  padding: 16rpx 20rpx;
  border: 1rpx solid var(--ui-border);
  border-radius: 14rpx;
  background: #ffffff;
  color: var(--ui-text);
  font-size: 14px;
  font-weight: 700;
  text-align: center;
  transition: transform 160ms ease, background-color 160ms ease, border-color 160ms ease;
}

.type-chip:active {
  transform: scale(0.97);
}

.type-chip--active {
  border-color: var(--ui-link);
  background: var(--ui-soft);
  color: var(--ui-link);
}

.type-chip--disabled {
  opacity: 0.45;
}

.stepper {
  display: flex;
  align-items: center;
  overflow: hidden;
  border: 1rpx solid var(--ui-border);
  border-radius: 12rpx;
}

.stepper__button {
  width: 44px;
  height: 44px;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: 0;
  background: #f6f8fb;
  color: var(--ui-link);
  font-size: 34rpx;
}

.stepper__value {
  width: 86rpx;
  color: var(--ui-text);
  font-size: 30rpx;
  font-weight: 800;
  text-align: center;
}

.mode-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 16rpx;
  margin-top: 8rpx;
}

.mode-card {
  min-height: 150rpx;
  padding: 22rpx;
  border: 1rpx solid var(--ui-border);
  border-radius: 16rpx;
  background: #ffffff;
  transition: transform 180ms ease, background-color 180ms ease, border-color 180ms ease, box-shadow 180ms ease;
}

.mode-card--active {
  border-color: var(--ui-link);
  background: var(--ui-soft);
  box-shadow: 0 8rpx 22rpx rgba(47, 127, 214, 0.10);
}

.mode-card:active {
  transform: scale(0.985);
}

.mode-card__title,
.mode-card__desc {
  display: block;
}

.mode-card__title {
  color: var(--ui-text);
  font-size: 29rpx;
  font-weight: 800;
}

.mode-card__desc {
  margin-top: 10rpx;
  color: var(--ui-muted);
  font-size: 14px;
  line-height: 1.5;
}

.tips-card__title,
.tips-card__line {
  display: block;
}

.tips-card__title {
  color: var(--ui-text);
  font-size: 30rpx;
  font-weight: 800;
}

.tips-card__line {
  margin-top: 12rpx;
  color: var(--ui-muted);
  font-size: 14px;
  line-height: 1.6;
}

.year-overlay {
  position: fixed;
  top: 0;
  right: 0;
  bottom: 0;
  left: 0;
  z-index: 1000;
  display: flex;
  align-items: flex-end;
  justify-content: center;
  background: rgba(15, 23, 42, 0.4);
  animation: prepare-year-mask-in 180ms ease-out both;
}

.year-modal {
  width: 100%;
  max-height: 60vh;
  overflow-y: auto;
  border-radius: 24rpx 24rpx 0 0;
  padding-bottom: env(safe-area-inset-bottom);
  animation: prepare-year-sheet-up 220ms ease-out both;
}

.year-checkbox {
  min-height: 48px;
  display: flex;
  align-items: center;
  gap: 16rpx;
  padding: 22rpx 0;
  border-bottom: 1rpx solid #eef2f6;
  color: var(--ui-text);
  font-size: 14px;
}

@keyframes prepare-year-mask-in {
  from {
    opacity: 0;
  }
  to {
    opacity: 1;
  }
}

@keyframes prepare-year-sheet-up {
  from {
    opacity: 0;
    transform: translate3d(0, 36rpx, 0);
  }
  to {
    opacity: 1;
    transform: translate3d(0, 0, 0);
  }
}
</style>
