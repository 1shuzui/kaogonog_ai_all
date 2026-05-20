<template>
  <view class="page">
    <text class="page-title">{{ pageTitle }}</text>
    <text class="page-desc">{{ pageDesc }}</text>

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
        <text class="section-title">练习配置</text>
      </view>

      <view v-if="showPracticeConfig" class="config-row">
        <text>题目数量</text>
        <view class="stepper">
          <button class="stepper__button" @tap="decreaseCount">-</button>
          <text class="stepper__value">{{ count }}</text>
          <button class="stepper__button" @tap="increaseCount">+</button>
        </view>
      </view>

      <view class="config-row">
        <text>练习模式</text>
      </view>
      <view class="mode-grid">
        <view class="mode-card" :class="{ 'mode-card--active': mode === 'free' }" @tap.stop="selectFreeMode">
          <text class="mode-card__title">专项练习</text>
          <text class="mode-card__desc">适合专项训练和即时复盘</text>
        </view>
        <view class="mode-card" :class="{ 'mode-card--active': mode === 'fullExam' }" @tap.stop="selectFullExamMode">
          <text class="mode-card__title">全真模拟</text>
          <text class="mode-card__desc">按真题套卷连续作答</text>
        </view>
      </view>

      <view v-if="mode === 'fullExam'" class="suite-panel">
        <view class="config-row config-row--suite">
          <text>真题套卷</text>
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
            <text class="suite-picker__arrow">切换</text>
          </view>
        </picker>
        <text v-if="selectedFullExamSuite" class="suite-panel__summary">{{ selectedFullExamSuiteSummary }}</text>
        <text v-else class="suite-panel__summary">{{ fullExamSuitesLoading ? '正在加载真题套卷...' : '当前省份暂无整套真题套卷，请切换江苏、安徽或湖南。' }}</text>
      </view>

      <view class="config-row media-row">
        <text>录制方式</text>
      </view>
      <view class="mode-grid">
        <view class="mode-card" :class="{ 'mode-card--active': mediaMode === 'audio' }" @tap.stop="selectAudioMode">
          <text class="mode-card__title">仅录音</text>
          <text class="mode-card__desc">不启用摄像头，真机调试更稳定</text>
        </view>
        <view class="mode-card" :class="{ 'mode-card--active': mediaMode === 'video' }" @tap.stop="selectVideoMode">
          <text class="mode-card__title">录像+录音</text>
          <text class="mode-card__desc">启用前置摄像头，同步记录视频</text>
        </view>
      </view>

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
    </view>

    <view class="card tips-card">
      <text class="tips-card__title">开考前检查</text>
      <text class="tips-card__line">保持环境安静，进入考场后请授权麦克风和摄像头。</text>
      <text class="tips-card__line">真机调试时，后端地址需使用手机可访问的域名或局域网 IP。</text>
    </view>

    <button
      v-if="!readonlyMode"
      class="primary-button"
      :disabled="loading || asrUnavailable"
      :loading="loading"
      @tap="startPractice"
    >
      {{ asrUnavailable ? '语音服务未就绪' : '进入考场' }}
    </button>
  </view>
</template>

<script setup>
import { computed, ref, watch } from 'vue'
import { onLoad, onShow } from '@dcloudio/uni-app'
import { useExamStore } from '../../stores/exam'
import { useBillingStore } from '../../stores/billing'
import { useQuestionBankStore } from '../../stores/questionBank'
import { useSubscriptionStore } from '../../stores/subscription'
import { useUserStore } from '../../stores/user'
import { getQuestionById, getQuestions } from '../../api/questionBank'
import { getAsrStatus } from '../../api/scoring'
import { getTrialQuestion, getTrialStatus } from '../../api/trial'
import { hideLoading, requireLogin, showLoading, toast } from '../../utils/navigation'
import { QUESTION_CATEGORIES } from '../../utils/constants'
import {
  fetchFullExamSuites,
  getFullExamSuiteSummary,
  loadFullExamSuiteQuestions
} from '../../utils/fullExamSuites'

const examStore = useExamStore()
const billingStore = useBillingStore()
const questionBankStore = useQuestionBankStore()
const subscriptionStore = useSubscriptionStore()
const userStore = useUserStore()
const DEFAULT_EXAM_QUESTION_COUNT = 5
const JIANGSU_FULL_EXAM_TIMING_MODE = 'jiangsu_5_15'
const MAX_FREE_QUESTION_COUNT = 10
const STATE_REFRESH_TIMEOUT_MS = 6000
const ENTER_ROOM_TIMEOUT_MS = 10000
const count = ref(DEFAULT_EXAM_QUESTION_COUNT)
const mode = ref('free')
const mediaMode = ref('audio')
const selectedDimensions = ref(['random'])
const selectedFullExamSuiteId = ref('')
const fullExamSuites = ref([])
const fullExamSuitesLoading = ref(false)
const loading = ref(false)
const accessLoading = ref(false)
const trial = ref(false)
const trialStatus = ref(null)
const asrStatus = ref(null)
const hasFullAccess = computed(() => {
  return billingStore.isPaid
    || subscriptionStore.hasPremiumAccess
    || userStore.isAdmin
    || userStore.userInfo?.billing?.isPaid === true
    || userStore.userInfo?.permissions?.canAccessPremiumModules === true
})
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
const showPracticeConfig = computed(() => mode.value === 'free')
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

watch(() => userStore.selectedProvince, () => {
  refreshFullExamSuites().catch(() => null)
}, { immediate: true })

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

function applyFullExamTimingMode(questions = []) {
  if (mode.value !== 'fullExam') return questions
  return questions.map((question) => ({
    ...question,
    fullExamTimingMode: question?.fullExamTimingMode || (userStore.selectedProvince === 'jiangsu' ? JIANGSU_FULL_EXAM_TIMING_MODE : '')
  }))
}

async function refreshFullExamSuites() {
  if (!hasFullAccess.value) {
    fullExamSuites.value = []
    selectedFullExamSuiteId.value = ''
    return
  }
  fullExamSuitesLoading.value = true
  try {
    const suites = await fetchFullExamSuites(getQuestions, userStore.selectedProvince)
    fullExamSuites.value = suites
  } catch (error) {
    fullExamSuites.value = []
    toast(error?.message || '真题套卷加载失败，请稍后重试')
  } finally {
    fullExamSuitesLoading.value = false
  }
}

onLoad((query) => {
  if (String(query?.mode || '') === 'fullExam') {
    mode.value = 'fullExam'
  } else if (String(query?.mode || '') === 'free') {
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

onShow(() => {
  loading.value = false
  accessLoading.value = false
  hideLoading()
  refreshAccessState()
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

async function refreshAccessState(options = {}) {
  if (!userStore.isAuthenticated) return false
  const timeoutMs = Number(options.timeout || STATE_REFRESH_TIMEOUT_MS)
  accessLoading.value = true
  try {
    await withTimeout(
      Promise.allSettled([
        userStore.loadUserInfo(),
        subscriptionStore.refresh({ skipErrorHandler: true })
      ]),
      timeoutMs,
      null
    )
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
    return hasFullAccess.value
  } finally {
    accessLoading.value = false
  }
}

async function refreshAsrStatus(options = {}) {
  if (!userStore.isAuthenticated) return
  const timeoutMs = Number(options.timeout || STATE_REFRESH_TIMEOUT_MS)
  asrStatus.value = await withTimeout(
    getAsrStatus({ skipErrorHandler: true }),
    timeoutMs,
    null
  )
}

function selectFreeMode() {
  mode.value = 'free'
}

function selectFullExamMode() {
  mode.value = 'fullExam'
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
  if (loading.value) return
  loading.value = true
  showLoading('检查考场')
  try {
    await refreshAccessState({ timeout: STATE_REFRESH_TIMEOUT_MS }).catch(() => null)
    await refreshAsrStatus({ timeout: STATE_REFRESH_TIMEOUT_MS }).catch(() => null)
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
        const access = await withTimeout(
          subscriptionStore.check(mode.value === 'fullExam' ? 'fullExam' : 'practice', { skipErrorHandler: true }),
          ENTER_ROOM_TIMEOUT_MS,
          { timeout: true }
        )
        if (access?.timeout) {
          toast('套餐权限校验超时，请稍后重试')
          return
        }
        if (access && access.allowed === false) {
          toast(access.reason || '当前套餐额度不足')
          return
        }
      }
      questions = await withTimeout(
        mode.value === 'fullExam'
          ? loadFullExamSuiteQuestions(selectedFullExamSuite.value, getQuestionById)
          : questionBankStore.fetchRandom({
            province: userStore.selectedProvince,
            count: count.value,
            dimension: selectedDimensionParam.value
          }),
        ENTER_ROOM_TIMEOUT_MS,
        []
      )
    }

    if (!questions.length) {
      toast(trial.value ? '试用题暂不可用，请稍后重试' : mode.value === 'fullExam' ? '当前省份暂无整套真题套卷' : '当前筛选条件暂无题目')
      return
    }
    if (mode.value === 'fullExam' && selectedFullExamSuite.value && questions.length !== selectedFullExamSuite.value.questions.length) {
      toast('当前套题题目加载不完整，请切换其他套卷后重试')
      return
    }
    const targetCount = trial.value ? 1 : mode.value === 'fullExam' ? questions.length : count.value
    const preparedQuestions = applyFullExamTimingMode(applyUserPracticePreferencesToQuestions(questions.slice(0, targetCount)))
    examStore.setMediaMode(mediaMode.value)
    await examStore.startFromQuestions(preparedQuestions, trial.value ? 'trial' : mode.value)
    uni.navigateTo({ url: '/pages/exam/room' })
  } catch (error) {
    toast(error?.message || '进入考场失败')
  } finally {
    loading.value = false
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
  color: #1a1a2e;
  font-size: 30rpx;
  font-weight: 800;
}

.access-card__desc,
.service-card__desc {
  margin-top: 10rpx;
  color: #5f6f83;
  font-size: 24rpx;
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
  color: #2a3648;
  font-size: 28rpx;
  font-weight: 600;
}

.config-row__value {
  flex: 1;
  margin-left: 24rpx;
  color: #1b5faa;
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
  border: 1rpx solid #d9e3ef;
  border-radius: 14rpx;
  background: #f8fbff;
}

.suite-picker {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 18rpx;
  min-height: 74rpx;
  padding: 0 18rpx;
  border: 1rpx solid #bfd7ef;
  border-radius: 12rpx;
  background: #ffffff;
  color: #1a1a2e;
  font-size: 25rpx;
  font-weight: 700;
}

.suite-picker__arrow {
  flex-shrink: 0;
  color: #1b5faa;
  font-size: 23rpx;
}

.suite-panel__summary {
  display: block;
  margin-top: 12rpx;
  color: #5f6f83;
  font-size: 23rpx;
  line-height: 1.6;
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
  min-width: 148rpx;
  padding: 16rpx 20rpx;
  border: 1rpx solid #d9e3ef;
  border-radius: 14rpx;
  background: #ffffff;
  color: #2a3648;
  font-size: 25rpx;
  font-weight: 700;
  text-align: center;
}

.type-chip--active {
  border-color: #1b5faa;
  background: #e8f4fd;
  color: #1b5faa;
}

.type-chip--disabled {
  opacity: 0.45;
}

.stepper {
  display: flex;
  align-items: center;
  overflow: hidden;
  border: 1rpx solid #d9e3ef;
  border-radius: 12rpx;
}

.stepper__button {
  width: 76rpx;
  height: 68rpx;
  border-radius: 0;
  background: #f6f8fb;
  color: #1b5faa;
  font-size: 34rpx;
}

.stepper__value {
  width: 86rpx;
  color: #1a1a2e;
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
  border: 1rpx solid #d9e3ef;
  border-radius: 16rpx;
  background: #ffffff;
}

.mode-card--active {
  border-color: #1b5faa;
  background: #e8f4fd;
}

.mode-card__title,
.mode-card__desc {
  display: block;
}

.mode-card__title {
  color: #1a1a2e;
  font-size: 29rpx;
  font-weight: 800;
}

.mode-card__desc {
  margin-top: 10rpx;
  color: #6f7c8f;
  font-size: 23rpx;
  line-height: 1.5;
}

.tips-card__title,
.tips-card__line {
  display: block;
}

.tips-card__title {
  color: #1a1a2e;
  font-size: 30rpx;
  font-weight: 800;
}

.tips-card__line {
  margin-top: 12rpx;
  color: #6f7c8f;
  font-size: 24rpx;
  line-height: 1.6;
}
</style>
