<template>
  <view class="page page--tab">
    <view class="home-hero">
      <view>
        <text class="home-hero__kicker">{{ userStore.selectedProvinceName }}备考</text>
        <text class="home-hero__title">公考面试AI测评</text>
        <text class="home-hero__desc">智能评分、精准诊断、高效提分</text>
      </view>
      <ScoreRing
        :score="historyStore.averageScore"
        :max-score="100"
        size="medium"
        label="平均分"
        color="#ffffff"
      />
    </view>

    <StatGrid :items="statItems" />

    <view v-if="showPreferenceSetup" class="preference-modal" @touchmove.stop.prevent>
      <view class="preference-modal__mask"></view>
      <view class="preference-modal__panel" @touchmove.stop>
        <scroll-view class="preference-modal__scroll" scroll-y>
          <view class="preference-setup">
            <view class="preference-setup__head">
              <text class="preference-setup__kicker">首次练习偏好</text>
              <text class="preference-setup__title">选择备考地区和注重题型</text>
              <text class="preference-setup__desc">后续可在“我的”里修改；题型不选时系统会按随机题型练习。</text>
            </view>
            <picker :range="provinceNames" :value="onboardingProvinceIndex" @change="onOnboardingProvinceChange">
              <view class="preference-picker">
                <text>备考地区</text>
                <text>{{ onboardingProvinceName }}</text>
              </view>
            </picker>
            <view class="preference-chip-grid">
              <view
                v-for="item in preferredQuestionOptions"
                :key="item.key"
                class="preference-chip"
                :class="{ 'preference-chip--active': isOnboardingQuestionSelected(item.key) }"
                @tap="toggleOnboardingQuestion(item.key)"
              >
                <text>{{ item.name }}</text>
              </view>
            </view>
            <view class="preference-setup__actions">
              <button class="secondary-button" :disabled="preferenceSaving" @tap="skipPreferenceSetup">跳过</button>
              <button class="primary-button" :loading="preferenceSaving" @tap="savePreferenceSetup">保存偏好</button>
            </view>
          </view>
        </scroll-view>
      </view>
    </view>

    <view class="quick-grid">
      <button class="primary-button quick-grid__button" @tap="goPractice('free')">专项练习</button>
      <button class="primary-button quick-grid__button" @tap="goPractice('fullExam')">全真练习</button>
      <button class="secondary-button quick-grid__button" @tap="goPricing">套餐中心</button>
    </view>

    <view v-if="showJiangsuEntry" class="jiangsu-entry card">
      <view class="jiangsu-entry__head">
        <text class="jiangsu-entry__kicker">首页核心入口</text>
        <text class="jiangsu-entry__title">2026 江苏事业单位统考</text>
        <text class="jiangsu-entry__desc">分岗精准刷题，岗位优先一眼看懂。</text>
      </view>
      <view class="jiangsu-feature">
        <text class="jiangsu-feature__label">创新点</text>
        <view class="jiangsu-feature__copy">
          <text class="jiangsu-feature__title">本土岗位贴合度</text>
          <text class="jiangsu-feature__desc">围绕江苏省情、事业单位岗位系统和真实基层场景组织训练。</text>
        </view>
      </view>
      <view class="jiangsu-grid">
        <view
          v-for="job in jiangsuJobs"
          :key="job.key"
          class="jiangsu-card"
          @tap="goJiangsuJob(job.key)"
        >
          <text class="jiangsu-card__rank">{{ job.rank }}</text>
          <view class="jiangsu-card__copy">
            <text class="jiangsu-card__title">{{ job.title }}</text>
            <text v-if="job.subtitle" class="jiangsu-card__desc">{{ job.subtitle }}</text>
          </view>
          <text class="jiangsu-card__arrow">›</text>
        </view>
      </view>
    </view>

    <view class="section-toggle" @tap="toggleSection('recent')">
      <text class="section-title">近期练习</text>
      <view class="section-toggle__right">
        <text class="muted" @tap.stop="goHistory">查看全部</text>
        <text class="section-toggle__arrow">{{ sectionArrow('recent') }}</text>
      </view>
    </view>

    <view v-if="sectionOpen.recent && recentRecords.length">
      <view
        v-for="record in recentRecords"
        :key="record.examId"
        class="record-card card"
        @tap="openResult(record)"
      >
        <view class="record-card__main">
          <text class="record-card__title">{{ record.questionSummary || '全真模拟练习' }}</text>
          <text class="record-card__meta">{{ formatDate(record.completedAt || record.date) }} · {{ record.questionCount || 1 }} 题</text>
        </view>
        <ScoreRing :score="record.totalScore || 0" :max-score="record.maxScore || 100" size="small" />
      </view>
    </view>
    <view v-else-if="sectionOpen.recent" class="card">
      <EmptyState title="暂无练习记录" desc="完成一次模考后，这里会展示近期得分和趋势。" mark="0" />
    </view>

    <view v-if="historyStore.stats?.dimensionAverages?.length" class="section-toggle" @tap="toggleSection('ability')">
      <text class="section-title">能力概览</text>
      <text class="section-toggle__arrow">{{ sectionArrow('ability') }}</text>
    </view>
    <view v-if="sectionOpen.ability && historyStore.stats?.dimensionAverages?.length" class="card">
      <DimensionBars :dimensions="historyStore.stats.dimensionAverages" />
    </view>

    <view class="section-toggle" @tap="toggleSection('trend')">
      <text class="section-title">成绩趋势</text>
      <text class="section-toggle__arrow">{{ sectionArrow('trend') }}</text>
    </view>
    <view v-if="sectionOpen.trend" class="card trend-card">
      <view class="trend-tabs">
        <view
          v-for="item in trendOptions"
          :key="item.label"
          class="trend-tab"
          :class="{ 'trend-tab--active': trendLimit === item.value }"
          @tap="setTrendLimit(item.value)"
        >
          <text>{{ item.label }}</text>
        </view>
      </view>
      <scroll-view v-if="trendDisplayData.length" class="trend-chart-scroll" scroll-x>
        <view class="trend-chart" :style="trendChartContentStyle">
          <view class="trend-chart__plot">
            <view
              v-for="area in trendAreaColumns"
              :key="area.key"
              class="trend-chart__area-column"
              :style="area.style"
            ></view>
            <view
              v-for="segment in trendSegments"
              :key="segment.key"
              class="trend-chart__segment"
              :style="segment.style"
            ></view>
            <view
              v-for="point in trendPoints"
              :key="point.key"
              class="trend-chart__point"
              :style="point.style"
            >
              <text class="trend-chart__score">{{ point.scoreLabel }}</text>
            </view>
          </view>
          <view
            v-for="point in trendPoints"
            :key="`${point.key}-label`"
            class="trend-chart__label"
            :style="point.labelStyle"
          >
            <text>{{ point.label }}</text>
          </view>
        </view>
      </scroll-view>
      <EmptyState v-else title="暂无趋势数据" desc="完成几次练习后，这里会显示成绩变化。" mark="-" />
    </view>

    <view class="section-toggle" @tap="toggleSection('weakness')">
      <text class="section-title">薄弱维度分析</text>
      <text class="section-toggle__arrow">{{ sectionArrow('weakness') }}</text>
    </view>
    <view v-if="sectionOpen.weakness" class="card weakness-card">
      <view v-if="weaknessDimensions.length" class="weakness-list">
        <view v-for="item in weaknessDimensions" :key="item.name" class="weakness-item">
          <view class="weakness-item__head">
            <text>{{ item.name }}</text>
            <text :class="{ 'weakness-item__percent--weak': item.isWeak }">{{ item.percent }}%</text>
          </view>
          <view class="weakness-item__rail">
            <view
              class="weakness-item__bar"
              :class="{ 'weakness-item__bar--weak': item.isWeak }"
              :style="`width:${item.percent}%;`"
            ></view>
          </view>
          <text v-if="item.isWeak && item.tip" class="weakness-item__tip">{{ item.tip }}</text>
        </view>
      </view>
      <EmptyState v-else title="暂无维度数据" desc="完成评分后会生成薄弱维度建议。" mark="-" />
    </view>

    <view class="section-toggle" @tap="toggleSection('recommendation')">
      <text class="section-title">智能推荐练习</text>
      <view class="section-toggle__right">
        <text class="muted" @tap.stop="refreshRecommendations(true)">刷新</text>
        <text class="section-toggle__arrow">{{ sectionArrow('recommendation') }}</text>
      </view>
    </view>
    <view v-if="sectionOpen.recommendation" class="card recommendation-card">
      <view v-if="recommendationLoading" class="recommendation-status">正在匹配真实题库...</view>
      <view v-else-if="recommendations.length" class="recommendation-list">
        <view v-for="item in recommendations" :key="item.id" class="recommendation-item">
          <view class="recommendation-item__head">
            <text class="recommendation-item__tag">{{ getCategoryName(item.dimension) }}</text>
            <text class="recommendation-item__reason">{{ item.reason }}</text>
          </view>
          <text class="recommendation-item__stem">{{ item.stem }}</text>
          <view class="recommendation-item__footer">
            <text>难度 {{ item.difficulty }}/5</text>
            <button class="primary-button recommendation-item__button" @tap="startRecommendedPractice(item)">开始练习</button>
          </view>
        </view>
      </view>
      <view v-else class="recommendation-status">
        <text>{{ recommendationEmptyText }}</text>
      </view>
    </view>
  </view>
</template>

<script setup>
import { computed, ref } from 'vue'
import { onPullDownRefresh, onShow } from '@dcloudio/uni-app'
import DimensionBars from '../../components/DimensionBars.vue'
import EmptyState from '../../components/EmptyState.vue'
import ScoreRing from '../../components/ScoreRing.vue'
import StatGrid from '../../components/StatGrid.vue'
import { getRandomQuestions } from '../../api/questionBank'
import { useHistoryStore } from '../../stores/history'
import { useUserStore } from '../../stores/user'
import {
  DIMENSION_KEY_BY_NAME,
  DIMENSION_TIPS,
  PROVINCES,
  QUESTION_CATEGORIES,
  WEAK_THRESHOLD,
  getCategoryName
} from '../../utils/constants'
import { formatDate } from '../../utils/format'
import { JIANGSU_JOB_CATEGORIES } from '../../utils/jiangsuJobs'
import { requireLogin, toast } from '../../utils/navigation'

const historyStore = useHistoryStore()
const userStore = useUserStore()
const jiangsuJobs = JIANGSU_JOB_CATEGORIES
const HOME_SECTION_STATE_KEY = 'civil_home_section_state'
const RECOMMENDATION_PRACTICED_KEY = 'civil_mini_recommendation_practiced_questions'
const DEFAULT_SECTION_OPEN = {
  recent: true,
  ability: true,
  trend: true,
  weakness: true,
  recommendation: true
}
const trendOptions = [
  { value: 0, label: '全部' },
  { value: 5, label: '最近5次' },
  { value: 10, label: '最近10次' },
  { value: 20, label: '最近20次' }
]
const TREND_POINT_GAP = 86
const TREND_SIDE_PADDING = 42
const TREND_PLOT_HEIGHT = 128
const TREND_PLOT_TOP = 22
const TREND_BASELINE_Y = TREND_PLOT_TOP + TREND_PLOT_HEIGHT
const TREND_CURVE_STEPS = 8
const preferredQuestionOptions = QUESTION_CATEGORIES.filter((item) => item.key)

const showJiangsuEntry = computed(() => userStore.selectedProvince === 'jiangsu')
const hasFullAccess = computed(() => (
  userStore.isAdmin
  || userStore.userInfo?.billing?.isPaid === true
  || userStore.userInfo?.permissions?.canAccessPremiumModules === true
))
const sectionOpen = ref(readSectionOpenState())
const trendLimit = ref(0)
const preferenceSaving = ref(false)
const onboardingProvince = ref(userStore.selectedProvince || 'national')
const onboardingPreferredDimensions = ref([])
const recommendationLoading = ref(false)
const recommendations = ref([])
const recommendationSeed = ref(0)
const recentRecords = computed(() => (historyStore.records || []).slice(0, 3))
const statItems = computed(() => [
  { label: '练习次数', value: historyStore.stats?.totalExams || 0 },
  { label: '最高分', value: historyStore.bestScore || 0 },
  { label: '薄弱维度', value: historyStore.weakestDimension || '暂无' }
])
const showPreferenceSetup = computed(() => (
  userStore.isAuthenticated && userStore.preferences?.practicePreferenceConfirmed !== true
))
const provinceOptions = computed(() => userStore.provinces.length ? userStore.provinces : PROVINCES)
const provinceNames = computed(() => provinceOptions.value.map((item) => item.name))
const onboardingProvinceIndex = computed(() => Math.max(0, provinceOptions.value.findIndex((item) => item.code === onboardingProvince.value)))
const onboardingProvinceName = computed(() => provinceOptions.value[onboardingProvinceIndex.value]?.name || '国考')
const trendDisplayData = computed(() => {
  const list = Array.isArray(historyStore.trendData) ? historyStore.trendData : []
  return trendLimit.value > 0 ? list.slice(-trendLimit.value) : list
})
const trendChartWidth = computed(() => {
  const count = Math.max(1, trendDisplayData.value.length)
  return (count - 1) * TREND_POINT_GAP + TREND_SIDE_PADDING * 2
})
const trendChartContentStyle = computed(() => `width:${trendChartWidth.value}rpx;`)
const trendScale = computed(() => {
  const scores = trendDisplayData.value.map((item) => normalizeScoreValue(item.score))
  if (!scores.length) return { min: 40, max: 100 }
  const rawMin = Math.min(...scores)
  const rawMax = Math.max(...scores)
  if (rawMax === rawMin) {
    return {
      min: Math.max(0, rawMin - 8),
      max: Math.min(100, rawMax + 8)
    }
  }
  const padding = Math.max(4, (rawMax - rawMin) * 0.24)
  return {
    min: Math.max(0, rawMin - padding),
    max: Math.min(100, rawMax + padding)
  }
})
const trendPoints = computed(() => trendDisplayData.value.map((item, index) => {
  const score = normalizeScoreValue(item.score)
  const range = Math.max(1, trendScale.value.max - trendScale.value.min)
  const ratio = Math.min(1, Math.max(0, (score - trendScale.value.min) / range))
  const x = TREND_SIDE_PADDING + index * TREND_POINT_GAP
  const y = TREND_PLOT_TOP + (1 - ratio) * TREND_PLOT_HEIGHT
  return {
    key: `${index}-${item.date || item.label || item.score}`,
    x,
    y,
    label: item.label || `第${index + 1}次`,
    scoreLabel: normalizeScore(score),
    style: `left:${x}rpx;top:${y}rpx;`,
    labelStyle: `left:${Math.max(0, x - 44)}rpx;`
  }
}))
const trendCurvePoints = computed(() => {
  const points = trendPoints.value
  if (points.length <= 2) return points
  const samples = []
  for (let index = 0; index < points.length - 1; index += 1) {
    const p0 = points[Math.max(0, index - 1)]
    const p1 = points[index]
    const p2 = points[index + 1]
    const p3 = points[Math.min(points.length - 1, index + 2)]
    const steps = Math.max(3, TREND_CURVE_STEPS)
    for (let step = 0; step < steps; step += 1) {
      if (index > 0 && step === 0) continue
      const t = step / steps
      samples.push({
        key: `${p1.key}-${step}`,
        x: catmullRom(p0.x, p1.x, p2.x, p3.x, t),
        y: clampTrendY(catmullRom(p0.y, p1.y, p2.y, p3.y, t))
      })
    }
  }
  samples.push(points[points.length - 1])
  return samples
})
const trendSegments = computed(() => {
  const points = trendCurvePoints.value
  return points.slice(1).map((point, index) => {
    const previous = points[index]
    const dx = point.x - previous.x
    const dy = point.y - previous.y
    const width = Math.sqrt(dx * dx + dy * dy)
    const angle = Math.atan2(dy, dx) * 180 / Math.PI
    return {
      key: `${previous.key}-${point.key}`,
      style: `left:${previous.x}rpx;top:${previous.y}rpx;width:${width}rpx;transform:rotate(${angle}deg);`
    }
  })
})
const trendAreaColumns = computed(() => {
  const points = trendCurvePoints.value
  const stride = Math.max(1, Math.ceil(points.length / 72))
  return points
    .filter((_, index) => index % stride === 0)
    .map((point, index) => ({
      key: `area-${index}-${Math.round(point.x)}`,
      style: `left:${Math.max(0, point.x - 4)}rpx;top:${point.y}rpx;height:${Math.max(0, TREND_BASELINE_Y - point.y)}rpx;`
    }))
})
const weaknessDimensions = computed(() => {
  const averages = historyStore.stats?.dimensionAverages
  if (!Array.isArray(averages)) return []
  return averages
    .map((item) => {
      const maxScore = Number(item.maxScore || 0)
      const avg = Number(item.avg || 0)
      const percent = maxScore > 0 ? Math.round((avg / maxScore) * 100) : 0
      return {
        name: item.name,
        avg,
        maxScore,
        percent: Math.min(100, Math.max(0, percent)),
        key: DIMENSION_KEY_BY_NAME[item.name] || '',
        isWeak: maxScore > 0 && percent < WEAK_THRESHOLD,
        tip: DIMENSION_TIPS[item.name] || ''
      }
    })
    .sort((a, b) => a.percent - b.percent)
})
const weakDimensionKeys = computed(() => weaknessDimensions.value
  .filter((item) => item.isWeak && item.key)
  .map((item) => item.key)
  .filter((item, index, list) => list.indexOf(item) === index)
)
const recommendationEmptyText = computed(() => {
  if (!weakDimensionKeys.value.length) return '当前维度表现较均衡，完成更多练习后会继续更新推荐。'
  return '暂未匹配到新的真实题库推荐，可稍后刷新。'
})

onShow(() => {
  if (!requireLogin()) return
  loadHome()
})

onPullDownRefresh(async () => {
  await loadHome()
  uni.stopPullDownRefresh()
})

async function loadHome() {
  await Promise.allSettled([
    userStore.loadProvinces(),
    userStore.loadUserInfo(),
    historyStore.fetchRecords({ pageSize: 3 }),
    historyStore.fetchStats(),
    historyStore.fetchTrend()
  ])
  syncPreferenceSetupFromStore()
  await refreshRecommendations(false)
}

async function goPractice(mode = 'free') {
  await userStore.loadUserInfo().catch(() => null)
  const targetMode = mode === 'fullExam' ? 'fullExam' : 'free'
  const baseUrl = `/pages/exam/prepare?mode=${targetMode}`
  uni.navigateTo({ url: hasFullAccess.value ? baseUrl : `${baseUrl}&trial=1` })
}

function goPricing() {
  uni.navigateTo({ url: '/pages/pricing/index' })
}

function goJiangsuJob(category) {
  uni.navigateTo({ url: `/pages/jiangsu/job?category=${encodeURIComponent(category)}` })
}

function goHistory() {
  uni.navigateTo({ url: '/pages/history/index' })
}

function openResult(record) {
  uni.navigateTo({ url: `/pages/result/index?examId=${encodeURIComponent(record.examId)}` })
}

function readSectionOpenState() {
  try {
    const raw = uni.getStorageSync(HOME_SECTION_STATE_KEY)
    const parsed = raw ? JSON.parse(raw) : {}
    return { ...DEFAULT_SECTION_OPEN, ...(parsed || {}) }
  } catch {
    return { ...DEFAULT_SECTION_OPEN }
  }
}

function persistSectionOpenState() {
  try {
    uni.setStorageSync(HOME_SECTION_STATE_KEY, JSON.stringify(sectionOpen.value))
  } catch {
    // local UI preference only
  }
}

function toggleSection(key) {
  sectionOpen.value = {
    ...sectionOpen.value,
    [key]: sectionOpen.value[key] !== true
  }
  persistSectionOpenState()
}

function sectionArrow(key) {
  return sectionOpen.value[key] ? '⌃' : '⌄'
}

function normalizeScore(value) {
  const score = normalizeScoreValue(value)
  return Number.isInteger(score) ? String(score) : score.toFixed(1)
}

function normalizeScoreValue(value) {
  const score = Number(value || 0)
  return Number.isFinite(score) ? score : 0
}

function catmullRom(p0, p1, p2, p3, t) {
  const t2 = t * t
  const t3 = t2 * t
  return 0.5 * (
    (2 * p1)
    + (-p0 + p2) * t
    + (2 * p0 - 5 * p1 + 4 * p2 - p3) * t2
    + (-p0 + 3 * p1 - 3 * p2 + p3) * t3
  )
}

function clampTrendY(value) {
  return Math.min(TREND_BASELINE_Y, Math.max(TREND_PLOT_TOP, value))
}

function setTrendLimit(value) {
  trendLimit.value = Number(value) || 0
}

function syncPreferenceSetupFromStore() {
  onboardingProvince.value = userStore.selectedProvince || 'national'
  onboardingPreferredDimensions.value = Array.isArray(userStore.preferences?.preferredQuestionDimensions)
    ? [...userStore.preferences.preferredQuestionDimensions]
    : []
}

function onOnboardingProvinceChange(event) {
  const selected = provinceOptions.value[Number(event.detail.value)]
  onboardingProvince.value = selected?.code || 'national'
}

function isOnboardingQuestionSelected(key) {
  return onboardingPreferredDimensions.value.includes(key)
}

function toggleOnboardingQuestion(key) {
  if (!key) return
  if (isOnboardingQuestionSelected(key)) {
    onboardingPreferredDimensions.value = onboardingPreferredDimensions.value.filter((item) => item !== key)
    return
  }
  onboardingPreferredDimensions.value = [...onboardingPreferredDimensions.value, key]
}

async function savePreferenceSetup() {
  if (preferenceSaving.value) return
  preferenceSaving.value = true
  try {
    userStore.setProvince(onboardingProvince.value || 'national')
    await userStore.savePreferences({
      ...userStore.preferences,
      preferredQuestionDimensions: onboardingPreferredDimensions.value,
      practicePreferenceConfirmed: true
    })
    toast('练习偏好已保存', 'success')
  } finally {
    preferenceSaving.value = false
  }
}

async function skipPreferenceSetup() {
  if (preferenceSaving.value) return
  onboardingPreferredDimensions.value = []
  await savePreferenceSetup()
}

function loadPracticedRecommendationIds() {
  try {
    const raw = uni.getStorageSync(RECOMMENDATION_PRACTICED_KEY)
    const parsed = raw ? JSON.parse(raw) : []
    return new Set(Array.isArray(parsed) ? parsed.filter(Boolean) : [])
  } catch {
    return new Set()
  }
}

function markRecommendationPracticed(questionId) {
  if (!questionId) return
  const ids = loadPracticedRecommendationIds()
  ids.add(questionId)
  try {
    uni.setStorageSync(RECOMMENDATION_PRACTICED_KEY, JSON.stringify(Array.from(ids).slice(-300)))
  } catch {
    // local recommendation memory only
  }
}

async function refreshRecommendations(showResultToast = false) {
  if (!weakDimensionKeys.value.length) {
    recommendations.value = []
    return
  }
  recommendationLoading.value = true
  try {
    recommendationSeed.value += 1
    const practicedIds = loadPracticedRecommendationIds()
    const dimensions = weakDimensionKeys.value.slice(0, 3)
    const list = await getRandomQuestions({
      province: userStore.selectedProvince || 'national',
      dimension: dimensions.join(','),
      count: 18,
      refreshSeed: recommendationSeed.value
    })
    const next = []
    for (const question of Array.isArray(list) ? list : []) {
      if (!question?.id || practicedIds.has(question.id)) continue
      const dimension = question.dimension || dimensions[0] || 'analysis'
      next.push({
        ...question,
        dimension,
        difficulty: Math.min(5, Math.max(1, Number(question.scoringPoints?.length || 3))),
        reason: `${getCategoryName(dimension)}薄弱，按省份与历史表现推荐`
      })
    }
    recommendations.value = next.slice(0, 4)
    if (showResultToast) toast(recommendations.value.length ? '推荐已刷新' : '暂无新的推荐题', 'success')
  } catch {
    recommendations.value = []
    if (showResultToast) toast('推荐加载失败，请稍后重试')
  } finally {
    recommendationLoading.value = false
  }
}

function startRecommendedPractice(item) {
  if (!item?.id) return
  markRecommendationPracticed(item.id)
  uni.navigateTo({ url: `/pages/exam/prepare?mode=free&questionId=${encodeURIComponent(item.id)}` })
}
</script>

<style scoped>
.home-hero {
  display: flex;
  align-items: center;
  justify-content: space-between;
  min-height: 240rpx;
  margin-bottom: 20rpx;
  padding: 32rpx;
  border-radius: 18rpx;
  background: linear-gradient(135deg, #15477a 0%, #1b5faa 62%, #5fa0e8 100%);
  color: #ffffff;
  box-shadow: 0 18rpx 40rpx rgba(21, 71, 122, 0.2);
}

.home-hero__kicker,
.home-hero__title,
.home-hero__desc {
  display: block;
}

.home-hero__kicker {
  opacity: 0.84;
  font-size: 24rpx;
}

.home-hero__title {
  margin-top: 12rpx;
  font-size: 42rpx;
  font-weight: 800;
}

.home-hero__desc {
  margin-top: 10rpx;
  opacity: 0.86;
  font-size: 25rpx;
}

.quick-grid {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 12rpx;
  margin-bottom: 28rpx;
}

.quick-grid__button {
  min-height: 82rpx;
  padding: 0 8rpx;
  font-size: 26rpx;
  font-weight: 800;
}

.preference-modal {
  position: fixed;
  top: 0;
  right: 0;
  bottom: 0;
  left: 0;
  z-index: 1000;
}

.preference-modal__mask {
  position: absolute;
  top: 0;
  right: 0;
  bottom: 0;
  left: 0;
  background: rgba(18, 24, 38, 0.48);
}

.preference-modal__panel {
  position: absolute;
  top: 50%;
  right: 32rpx;
  left: 32rpx;
  max-height: calc(100vh - 168rpx);
  overflow: hidden;
  border-radius: 18rpx;
  background: #ffffff;
  box-shadow: 0 24rpx 80rpx rgba(18, 24, 38, 0.18);
  transform: translateY(-50%);
}

.preference-modal__scroll {
  max-height: calc(100vh - 168rpx);
}

.preference-setup {
  padding: 30rpx;
}

.preference-setup__kicker,
.preference-setup__title,
.preference-setup__desc {
  display: block;
}

.preference-setup__kicker {
  color: #1b5faa;
  font-size: 23rpx;
  font-weight: 800;
}

.preference-setup__title {
  margin-top: 8rpx;
  color: #1a1a2e;
  font-size: 32rpx;
  font-weight: 900;
}

.preference-setup__desc {
  margin-top: 8rpx;
  color: #6f7c8f;
  font-size: 23rpx;
  line-height: 1.5;
}

.preference-picker {
  display: flex;
  justify-content: space-between;
  margin-top: 22rpx;
  padding: 18rpx 0;
  border-top: 1rpx solid #eef2f6;
  border-bottom: 1rpx solid #eef2f6;
  color: #2a3648;
  font-size: 26rpx;
}

.preference-picker text:last-child {
  color: #1b5faa;
  font-weight: 800;
}

.preference-chip-grid {
  display: flex;
  flex-wrap: wrap;
  gap: 12rpx;
  margin-top: 18rpx;
}

.preference-chip {
  padding: 12rpx 18rpx;
  border: 1rpx solid #d9e3ef;
  border-radius: 999rpx;
  background: #ffffff;
  color: #2a3648;
  font-size: 24rpx;
  font-weight: 700;
}

.preference-chip--active {
  border-color: #1b5faa;
  background: #e8f4fd;
  color: #1b5faa;
}

.preference-setup__actions {
  display: grid;
  grid-template-columns: 180rpx minmax(0, 1fr);
  gap: 16rpx;
  margin-top: 22rpx;
}

.section-toggle {
  display: flex;
  align-items: center;
  justify-content: space-between;
  min-height: 74rpx;
  margin-top: 18rpx;
  padding: 0 4rpx;
}

.section-toggle__right {
  display: flex;
  align-items: center;
  gap: 18rpx;
}

.section-toggle__arrow {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 46rpx;
  height: 46rpx;
  border-radius: 999rpx;
  background: #eef5fc;
  color: #1b5faa;
  font-size: 26rpx;
  font-weight: 900;
}

.trend-card {
  padding: 24rpx;
}

.trend-tabs {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 12rpx;
}

.trend-tab {
  padding: 14rpx 10rpx;
  border: 1rpx solid #d9e3ef;
  border-radius: 12rpx;
  background: #ffffff;
  color: #5f6f83;
  font-size: 23rpx;
  font-weight: 800;
  text-align: center;
}

.trend-tab--active {
  border-color: #1b5faa;
  background: #e8f4fd;
  color: #1b5faa;
}

.trend-chart-scroll {
  margin-top: 18rpx;
  width: 100%;
}

.trend-chart {
  position: relative;
  min-width: 100%;
  height: 220rpx;
  border-bottom: 1rpx solid #e8eef5;
  background:
    linear-gradient(180deg, rgba(232, 238, 245, 0.68) 1rpx, transparent 1rpx) 0 22rpx / 100% 32rpx no-repeat,
    linear-gradient(180deg, rgba(232, 238, 245, 0.52) 1rpx, transparent 1rpx) 0 54rpx / 100% 32rpx no-repeat,
    linear-gradient(180deg, rgba(232, 238, 245, 0.42) 1rpx, transparent 1rpx) 0 86rpx / 100% 32rpx no-repeat,
    linear-gradient(180deg, rgba(232, 238, 245, 0.32) 1rpx, transparent 1rpx) 0 118rpx / 100% 32rpx no-repeat;
}

.trend-chart__plot {
  position: absolute;
  top: 0;
  right: 0;
  left: 0;
  height: 168rpx;
}

.trend-chart__area-column {
  position: absolute;
  width: 8rpx;
  border-radius: 999rpx 999rpx 0 0;
  background: linear-gradient(180deg, rgba(27, 95, 170, 0.18) 0%, rgba(27, 95, 170, 0.02) 100%);
}

.trend-chart__segment {
  position: absolute;
  height: 4rpx;
  border-radius: 999rpx;
  background: #1b5faa;
  box-shadow: 0 4rpx 12rpx rgba(27, 95, 170, 0.16);
  transform-origin: left center;
}

.trend-chart__point {
  position: absolute;
  width: 18rpx;
  height: 18rpx;
  margin-top: -9rpx;
  margin-left: -9rpx;
  border: 5rpx solid #1b5faa;
  border-radius: 999rpx;
  background: #ffffff;
  box-shadow: 0 6rpx 18rpx rgba(27, 95, 170, 0.22);
}

.trend-chart__score {
  position: absolute;
  left: 50%;
  bottom: 22rpx;
  display: block;
  min-width: 58rpx;
  font-size: 20rpx;
  color: #1b5faa;
  font-weight: 900;
  line-height: 1.2;
  text-align: center;
  transform: translateX(-50%);
}

.trend-chart__label {
  position: absolute;
  bottom: 0;
  display: block;
  width: 88rpx;
  overflow: hidden;
  color: #6f7c8f;
  font-size: 21rpx;
  line-height: 1.2;
  text-align: center;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.weakness-card,
.recommendation-card {
  padding: 24rpx;
}

.weakness-list,
.recommendation-list {
  display: flex;
  flex-direction: column;
  gap: 18rpx;
}

.weakness-item__head {
  display: flex;
  justify-content: space-between;
  color: #2a3648;
  font-size: 25rpx;
  font-weight: 800;
}

.weakness-item__percent--weak {
  color: #cf1322;
}

.weakness-item__rail {
  height: 12rpx;
  margin-top: 10rpx;
  border-radius: 999rpx;
  background: #edf2f7;
  overflow: hidden;
}

.weakness-item__bar {
  height: 100%;
  border-radius: 999rpx;
  background: #1b5faa;
}

.weakness-item__bar--weak {
  background: #cf1322;
}

.weakness-item__tip {
  display: block;
  margin-top: 10rpx;
  padding: 12rpx 14rpx;
  border-left: 4rpx solid #d48806;
  border-radius: 8rpx;
  background: #fff8eb;
  color: #6f4a12;
  font-size: 22rpx;
  line-height: 1.55;
}

.recommendation-status {
  padding: 28rpx 0;
  color: #6f7c8f;
  font-size: 24rpx;
  text-align: center;
}

.recommendation-item {
  padding: 18rpx;
  border: 1rpx solid #d9e3ef;
  border-radius: 14rpx;
  background: #f8fbff;
}

.recommendation-item__head {
  display: flex;
  align-items: center;
  gap: 12rpx;
  margin-bottom: 12rpx;
}

.recommendation-item__tag {
  flex: 0 0 auto;
  padding: 6rpx 14rpx;
  border-radius: 999rpx;
  background: #e8f4fd;
  color: #1b5faa;
  font-size: 21rpx;
  font-weight: 800;
}

.recommendation-item__reason {
  min-width: 0;
  overflow: hidden;
  color: #6f7c8f;
  font-size: 22rpx;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.recommendation-item__stem {
  display: -webkit-box;
  overflow: hidden;
  color: #1f2b3d;
  font-size: 25rpx;
  font-weight: 650;
  line-height: 1.55;
  -webkit-box-orient: vertical;
  -webkit-line-clamp: 3;
}

.recommendation-item__footer {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16rpx;
  margin-top: 14rpx;
  color: #8a5a00;
  font-size: 22rpx;
  font-weight: 700;
}

.recommendation-item__button {
  flex: 0 0 168rpx;
  min-height: 64rpx;
  font-size: 23rpx;
}

.jiangsu-entry {
  padding: 26rpx;
}

.jiangsu-entry__kicker,
.jiangsu-entry__title,
.jiangsu-entry__desc {
  display: block;
}

.jiangsu-entry__kicker {
  color: #1b5faa;
  font-size: 23rpx;
  font-weight: 700;
}

.jiangsu-entry__title {
  margin-top: 8rpx;
  color: #1a1a2e;
  font-size: 34rpx;
  font-weight: 900;
}

.jiangsu-entry__desc {
  margin-top: 8rpx;
  color: #6f7c8f;
  font-size: 24rpx;
}

.jiangsu-grid {
  display: flex;
  flex-direction: column;
  gap: 14rpx;
  margin-top: 22rpx;
}

.jiangsu-feature {
  display: grid;
  grid-template-columns: 104rpx minmax(0, 1fr);
  gap: 16rpx;
  align-items: center;
  margin-top: 20rpx;
  padding: 18rpx;
  border: 1rpx solid #d9e3ef;
  border-radius: 14rpx;
  background: #f5f9fe;
}

.jiangsu-feature__label,
.jiangsu-feature__title,
.jiangsu-feature__desc {
  display: block;
}

.jiangsu-feature__label {
  padding: 8rpx 12rpx;
  border-radius: 999rpx;
  background: #1b5faa;
  color: #ffffff;
  font-size: 22rpx;
  font-weight: 800;
  text-align: center;
}

.jiangsu-feature__copy {
  min-width: 0;
}

.jiangsu-feature__title {
  color: #1a1a2e;
  font-size: 27rpx;
  font-weight: 900;
}

.jiangsu-feature__desc {
  margin-top: 6rpx;
  color: #5f6f83;
  font-size: 23rpx;
  line-height: 1.5;
}

.jiangsu-card {
  display: grid;
  grid-template-columns: 54rpx minmax(0, 1fr) 28rpx;
  gap: 16rpx;
  align-items: center;
  min-height: 100rpx;
  padding: 18rpx;
  border: 1rpx solid #d9e3ef;
  border-radius: 14rpx;
  background: #ffffff;
}

.jiangsu-card__rank {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 54rpx;
  height: 54rpx;
  border-radius: 999rpx;
  background: #e8f4fd;
  color: #1b5faa;
  font-size: 25rpx;
  font-weight: 900;
}

.jiangsu-card__title,
.jiangsu-card__desc {
  display: block;
}

.jiangsu-card__title {
  overflow: hidden;
  color: #1a1a2e;
  font-size: 28rpx;
  font-weight: 800;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.jiangsu-card__desc {
  margin-top: 6rpx;
  overflow: hidden;
  color: #6f7c8f;
  font-size: 23rpx;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.jiangsu-card__arrow {
  color: #8c8c8c;
  font-size: 44rpx;
  line-height: 1;
}

.record-card {
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.record-card__main {
  min-width: 0;
  padding-right: 22rpx;
}

.record-card__title {
  display: -webkit-box;
  overflow: hidden;
  color: #1f2b3d;
  font-size: 29rpx;
  font-weight: 600;
  line-height: 1.5;
  -webkit-box-orient: vertical;
  -webkit-line-clamp: 2;
}

.record-card__meta {
  display: block;
  margin-top: 10rpx;
  color: #6f7c8f;
  font-size: 23rpx;
}
</style>
