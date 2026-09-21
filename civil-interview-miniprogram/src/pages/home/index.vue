<!--
小程序首页，负责展示可浏览入口、江苏事业单位入口、练习/定向/套餐入口和登录后个人概览。

未登录用户必须能先浏览功能结构，因此本页不能在 onShow/onLoad 强制索取手机号、头像或昵称。
需要账号的动作只在用户点击试用、开始练习、开通、历史、收藏或个人数据时触发登录拦截；登录后才加载成绩趋势、权益和偏好弹窗。

@param: 无；页面状态来自 Pinia、公开分类数据和用户点击。
@return: 渲染首页入口、公开说明、登录提示和登录后的个人概览。
@raises: 不主动抛业务异常；接口失败、未登录和权限不足由请求层或页面空态承接。
-->
<template>
  <view class="motion-page page page--tab learner-page learner-home" :class="motionClass" :style="motionStyle">
    <BackgroundAnswers @layout-change="calibrate" />
    <MotionSummary class="home-motion-summary" :compact="compact" title="面试练习" :detail="userStore.selectedProvinceName" />
    <view class="home-hero">
      <view>
        <text class="home-hero__kicker">{{ userStore.selectedProvinceName }} · 面试练习</text>
        <text class="home-hero__title">今天，开口练一练</text>
        <text class="home-hero__desc">专项练习 · 自选题型与题数</text>
        <button class="primary-button learner-home__start" @tap="goPractice('free')">{{ isLoggedIn ? '开始练习' : '登录后试用' }} →</button>
      </view>
      <view class="learner-home__sound"><MotionAccent class="home-motion-accent"><LearnerIcon name="audio" :size="28" /></MotionAccent></view>
    </view>

    <view class="quick-grid">
      <button class="secondary-button quick-grid__button" @tap="goPractice('fullExam')"><LearnerIcon name="read" />全真练习</button>
      <button class="secondary-button quick-grid__button" @tap="goPricing"><LearnerIcon name="wallet" />套餐中心</button>
    </view>

    <MotionCollapse v-if="isLoggedIn" class="home-section-recent" title="近期练习" :open="sectionOpen.recent" :revision="[recentRecords, historyStore.stats]" @toggle="toggleSection('recent')">
      <template #actions><button class="home-text-button" @tap.stop="goHistory">查看全部</button></template>
      <view v-if="recentRecords.length">
        <button
          v-for="record in recentRecords"
          :key="record.examId"
          class="record-card card"
          @tap="openResult(record)"
        >
          <view class="record-card__main">
            <text class="record-card__title">{{ record.questionSummary || '全真模拟练习' }}</text>
            <text class="record-card__meta">{{ formatDate(record.completedAt || record.date) }} · {{ record.questionCount || 1 }} 题</text>
            <text class="record-card__action">查看复盘 →</text>
          </view>
          <ScoreRing :score="record.totalScore || 0" :max-score="record.maxScore || 100" size="small" />
        </button>
      </view>
      <view v-else class="card home-first-practice">
        <text class="home-first-practice__title">从一次开口练习开始</text>
        <text class="home-first-practice__desc">完成练习后，在这里查看记录与点评。</text>
        <button class="secondary-button" @tap="goPractice('free')">开始首次练习</button>
      </view>
      <view v-if="historyStore.stats?.totalExams > 0" class="learner-home__overview">
        <view class="learner-home__average">
          <ScoreRing :score="historyStore.averageScore" :max-score="100" size="small" label="平均分" color="#326BE5" />
          <text class="muted">每次开口，都有进步的空间。</text>
        </view>
        <StatGrid :items="statItems" />
      </view>
    </MotionCollapse>

    <view v-if="!isLoggedIn" class="guest-tip card">
      <view class="guest-tip__copy">
        <text class="guest-tip__title">先浏览，想练时再登录</text>
        <text class="guest-tip__desc">先看看题库、题型和岗位方向；登录后可使用试用题并保存练习记录。</text>
      </view>
      <navigator class="secondary-button guest-tip__button" url="/pages/bank/index" open-type="switchTab">浏览题库</navigator>
    </view>

    <view v-if="showPreferenceSetup" class="preference-modal" @touchmove.stop.prevent>
      <view class="preference-modal__mask"></view>
      <view class="preference-modal__panel" @touchmove.stop>
        <scroll-view class="preference-modal__scroll" scroll-y>
          <view class="preference-setup">
            <view class="preference-setup__head">
              <text class="preference-setup__kicker">首次考试设置</text>
              <text class="preference-setup__title">选择备考地区、考试大类和注重题型</text>
              <text class="preference-setup__desc">后续可在“我的”里修改；题型不选时系统会按随机题型练习。</text>
            </view>
            <picker :range="provinceNames" :value="onboardingProvinceIndex" @change="onOnboardingProvinceChange">
              <view class="preference-picker">
                <text>备考地区</text>
                <text>{{ onboardingProvinceName }}</text>
              </view>
            </picker>
              <picker :range="onboardingExamCatNames" :value="onboardingExamCatIndex" @change="onOnboardingExamCatChange">
                <view class="preference-picker">
                  <text>考试大类</text>
                  <text>{{ onboardingExamCatName }}</text>
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

    <view class="practice-routes">
      <navigator class="practice-route" url="/pages/training/index" open-type="switchTab">
        <LearnerIcon name="aim" :size="24" />
        <view class="practice-route__copy"><text class="practice-route__title">题型训练</text><text class="practice-route__desc">按单一题型反复练习</text></view>
        <text class="practice-route__arrow">›</text>
      </navigator>
      <navigator class="practice-route" url="/pages/targeted/index" open-type="switchTab">
        <LearnerIcon name="environment" :size="24" />
        <view class="practice-route__copy"><text class="practice-route__title">定向备面</text><text class="practice-route__desc">按考试、地区与岗位选方向</text></view>
        <text class="practice-route__arrow">›</text>
      </navigator>
    </view>
    <view v-if="showJiangsuEntry" class="jiangsu-entry card">
      <MotionCollapse class="home-section-jiangsu" title="2026 江苏事业单位统考" :open="jiangsuExpanded" @toggle="jiangsuExpanded = !jiangsuExpanded">
      <view class="jiangsu-grid">
        <button
          v-for="job in jiangsuJobs"
          :key="job.key"
          class="jiangsu-card"
          @tap="goJiangsuJob(job.key)"
        >
          <view class="jiangsu-card__copy">
            <text class="jiangsu-card__title">{{ job.title }}</text>
            <text v-if="job.subtitle" class="jiangsu-card__desc">{{ job.subtitle }}</text>
          </view>
          <text class="jiangsu-card__arrow">›</text>
        </button>
      </view>
      </MotionCollapse>
      <text class="jiangsu-entry__desc">{{ jiangsuExpanded ? '点击岗位查看题库' : `岗位题库 · ${jiangsuJobs.length} 个方向，展开选择` }}</text>
    </view>

    <MotionCollapse v-if="isLoggedIn && historyStore.stats?.dimensionAverages?.length" class="home-section-ability" title="能力概览" :open="sectionOpen.ability" :revision="historyStore.stats?.dimensionAverages" @toggle="toggleSection('ability')"><view class="card">
      <DimensionBars :dimensions="historyStore.stats?.dimensionAverages || []" />
    </view></MotionCollapse>

    <MotionCollapse v-if="isLoggedIn && historyStore.trendData?.length" class="home-section-trend" title="成绩趋势" :open="sectionOpen.trend" :revision="[trendLimit, trendDisplayData]" @toggle="toggleSection('trend')"><view class="card trend-card">
      <MotionSegmented class="home-trend-segment" :model-value="trendLimit" :options="trendOptions" @change="setTrendLimit" />
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
      <EmptyState v-else :title="isLoggedIn ? '暂无趋势数据' : '登录后查看成绩趋势'" :desc="isLoggedIn ? '完成几次练习后，这里会显示成绩变化。' : '浏览功能无需登录，开始试用或练习后会保存成绩趋势。'" mark="-" />
    </view></MotionCollapse>

    <MotionCollapse v-if="isLoggedIn && weaknessDimensions.length" class="home-section-weakness" title="薄弱维度分析" :open="sectionOpen.weakness" :revision="weaknessDimensions" @toggle="toggleSection('weakness')"><view class="card weakness-card">
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
      <EmptyState v-else :title="isLoggedIn ? '暂无维度数据' : '登录后查看薄弱维度'" :desc="isLoggedIn ? '完成评分后会生成薄弱维度建议。' : '答题评分后会在这里呈现维度短板。'" mark="-" />
    </view></MotionCollapse>

    <MotionCollapse v-if="isLoggedIn && (weakDimensionKeys.length || recommendationLoading || recommendations.length)" class="home-section-recommendation" title="智能推荐练习" :open="sectionOpen.recommendation" :revision="[recommendations, recommendationLoading, recommendationEmptyText]" @toggle="toggleSection('recommendation')">
      <template #actions><button class="home-text-button" @tap.stop="refreshRecommendations(true)">刷新</button></template>
      <view class="card recommendation-card">
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
    </view></MotionCollapse>
  </view>
</template>

<script setup>
import MotionSegmented from '../../components/MotionSegmented.vue'
import MotionCollapse from '../../components/MotionCollapse.vue'
import MotionAccent from '../../components/MotionAccent.vue'
import MotionSummary from '../../components/MotionSummary.vue'
import { useScrollSummary } from '../../motion/useScrollSummary'
const { compact, calibrate, onSummaryScroll } = useScrollSummary('.home-hero')
onPageScroll(onSummaryScroll)
import { usePageMotion } from '../../motion/useMotion'
const { motionClass, motionStyle } = usePageMotion()
import LearnerIcon from '../../components/LearnerIcon.vue'
import BackgroundAnswers from '../../components/BackgroundAnswers.vue'
import { computed, ref } from 'vue'
import { onPullDownRefresh, onShow, onPageScroll } from '@dcloudio/uni-app'
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
import { DEFAULT_TARGETED_POSITION_TREE } from '../../utils/targetedOptions'
import { hasToken, promptLoginForAction, toast } from '../../utils/navigation'

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

const isLoggedIn = computed(() => userStore.isAuthenticated || hasToken())
const showJiangsuEntry = computed(() => userStore.selectedProvince === 'jiangsu')
const hasFullAccess = computed(() => (
  userStore.isAdmin
  || userStore.userInfo?.billing?.isPaid === true
  || userStore.userInfo?.permissions?.canAccessPremiumModules === true
))
const sectionOpen = ref(readSectionOpenState())
const jiangsuExpanded = ref(false)
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
// Onboarding exam category
const onboardingExamCatId = ref('')
const examCatPrefOpts = DEFAULT_TARGETED_POSITION_TREE
const onboardingExamCatNames = computed(() => ['不限', ...examCatPrefOpts.map(c => c.name)])
const onboardingExamCatIndex = computed(() => {
  if (!onboardingExamCatId.value) return 0
  const idx = examCatPrefOpts.findIndex(c => String(c.id) === String(onboardingExamCatId.value))
  return idx >= 0 ? idx + 1 : 0
})
const onboardingExamCatName = computed(() => {
  const cat = examCatPrefOpts.find(c => String(c.id) === String(onboardingExamCatId.value))
  return cat ? cat.name : '不限'
})
function onOnboardingExamCatChange(e) {
  const idx = Number(e.detail.value)
  onboardingExamCatId.value = idx === 0 ? '' : (examCatPrefOpts[idx - 1]?.id || '')
}
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
  if (!isLoggedIn.value) return '登录后会根据练习记录推荐适合你的真实题。'
  if (!weakDimensionKeys.value.length) return '当前维度表现较均衡，完成更多练习后会继续更新推荐。'
  return '暂未匹配到新的真实题库推荐，可稍后刷新。'
})

onShow(() => {
  loadHome()
})

onPullDownRefresh(async () => {
  await loadHome()
  uni.stopPullDownRefresh()
})

async function loadHome() {
  if (!isLoggedIn.value) {
    recommendations.value = []
    return
  }
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
  const targetMode = mode === 'fullExam' ? 'fullExam' : 'free'
  const baseUrl = `/pages/exam/prepare?mode=${targetMode}`
  if (!promptLoginForAction(targetMode === 'fullExam' ? '全真练习' : '专项练习', baseUrl)) return
  await userStore.loadUserInfo().catch(() => null)
  uni.navigateTo({ url: hasFullAccess.value ? baseUrl : `${baseUrl}&trial=1` })
}

function goPricing() {
  if (!promptLoginForAction('开通套餐', '/pages/pricing/index')) return
  uni.navigateTo({ url: '/pages/pricing/index' })
}

function goJiangsuJob(category) {
  uni.navigateTo({ url: `/pages/jiangsu/job?category=${encodeURIComponent(category)}` })
}

function goHistory() {
  if (!promptLoginForAction('查看练习记录', '/pages/history/index')) return
  uni.navigateTo({ url: '/pages/history/index' })
}

function openResult(record) {
  if (!promptLoginForAction('查看测评结果', `/pages/result/index?examId=${encodeURIComponent(record.examId)}`)) return
  uni.navigateTo({ url: `/pages/result/index?examId=${encodeURIComponent(record.examId)}` })
}

function goLogin() {
  uni.navigateTo({ url: '/pages/login/index?redirect=%2Fpages%2Fhome%2Findex' })
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
  if (!promptLoginForAction('保存考试设置', '/pages/home/index')) return
  if (preferenceSaving.value) return
  preferenceSaving.value = true
  try {
    userStore.setProvince(onboardingProvince.value || 'national')
    await userStore.savePreferences({
      ...userStore.preferences,
      preferredQuestionDimensions: onboardingPreferredDimensions.value,
      practicePreferenceConfirmed: true,
      examCategory: onboardingExamCatId.value
        ? (examCatPrefOpts.find(c => String(c.id) === String(onboardingExamCatId.value))?.name || '')
        : ''
    })
    toast('考试设置已保存', 'success')
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
  if (!isLoggedIn.value) {
    recommendations.value = []
    if (showResultToast) promptLoginForAction('刷新智能推荐', '/pages/home/index')
    return
  }
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
  if (!promptLoginForAction('开始推荐练习', `/pages/exam/prepare?mode=free&questionId=${encodeURIComponent(item.id)}`)) return
  markRecommendationPracticed(item.id)
  uni.navigateTo({ url: `/pages/exam/prepare?mode=free&questionId=${encodeURIComponent(item.id)}` })
}
</script>

<style scoped>
.learner-page.learner-home .home-hero {
  display: flex;
  align-items: center;
  justify-content: space-between;
  min-height: 0;
  margin-bottom: 16px;
  padding: 16px;
  border: 0;
  border-radius: 12px;
  background: var(--ui-soft, #edf3ff);
  color: var(--ui-text, #203047);
  box-shadow: none;
  animation: motion-fade-up 240ms ease-out both;
}

.home-hero__kicker,
.home-hero__title,
.home-hero__desc {
  display: block;
}

.learner-page.learner-home .home-hero__kicker {
  color: var(--ui-muted, #596a80);
  font-size: 14px;
}

.learner-page.learner-home .home-hero__title {
  margin-top: 8px;
  color: var(--ui-text, #203047);
  font-size: 24px;
  line-height: 1.4;
  font-weight: 700;
}

.learner-page.learner-home .home-hero__desc {
  margin: 8px 0 16px;
  color: var(--ui-muted, #596a80);
  font-size: 14px;
  line-height: 1.5;
}

.learner-page.learner-home .learner-home__start {
  width: auto;
  max-width: calc(100% - 48px);
  min-height: 44px;
  padding: 8px 16px;
  font-size: 16px;
  background: var(--ui-primary, #326be5);
}

.learner-page.learner-home .learner-home__sound {
  right: 16px;
  bottom: 16px;
  width: 36px;
  height: 44px;
}

.learner-page.learner-home .quick-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 8px;
  margin: 12px 0 16px;
}

.learner-page.learner-home .quick-grid__button {
  flex-direction: row;
  gap: 8px;
  min-height: 44px;
  padding: 8px;
  border: 1px solid var(--ui-border, #dbe3ee);
  border-radius: 12px;
  color: var(--ui-link, #285bc7);
  font-size: 14px;
  font-weight: 500;
}

.learner-home .guest-tip {
  padding: 16px;
  margin-bottom: 16px;
}

.guest-tip__title,
.guest-tip__desc {
  display: block;
}

.guest-tip__title {
  color: var(--ui-text, #203047);
  font-size: 16px;
  font-weight: 700;
}

.guest-tip__desc {
  margin-top: 6rpx;
  color: var(--ui-muted, #596a80);
  font-size: 14px;
  line-height: 1.5;
}

.learner-home .guest-tip__button {
  display: flex;
  align-items: center;
  justify-content: center;
  min-height: 44px;
  margin-top: 12px;
  padding: 8px 16px;
  color: var(--ui-link, #285bc7);
  font-size: 14px;
}

.practice-routes {
  margin-top: 16px;
  border-top: 1px solid var(--ui-border, #dbe3ee);
}

.practice-route {
  display: flex;
  align-items: center;
  gap: 12px;
  min-height: 44px;
  padding: 12px 0;
  border-bottom: 1px solid var(--ui-border, #dbe3ee);
}

.practice-route__copy { flex: 1; min-width: 0; }
.practice-route__title, .practice-route__desc { display: block; }
.practice-route__title { color: var(--ui-text, #203047); font-size: 16px; font-weight: 600; }
.practice-route__desc { margin-top: 4px; color: var(--ui-muted, #596a80); font-size: 14px; line-height: 1.5; }
.practice-route__arrow { color: var(--ui-muted, #596a80); font-size: 24px; }

.home-text-button {
  display: flex;
  align-items: center;
  min-height: 44px;
  min-width: 44px;
  padding: 8px;
  background: transparent;
  color: var(--ui-link, #285bc7);
  font-size: 14px;
}

.home-first-practice__title, .home-first-practice__desc { display: block; }
.home-first-practice__title { color: var(--ui-text, #203047); font-size: 16px; font-weight: 600; }
.home-first-practice__desc { margin: 8px 0 16px; color: var(--ui-muted, #596a80); font-size: 14px; line-height: 1.6; }

.learner-home button:focus-visible, .learner-home navigator:focus-visible {
  outline: 2px solid var(--ui-link, #285bc7);
  outline-offset: 2px;
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
  animation: preference-mask-in 180ms ease-out both;
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
  animation: preference-panel-in 220ms ease-out both;
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
  color: var(--ui-link, #285bc7);
  font-size: 23rpx;
  font-weight: 800;
}

.preference-setup__title {
  margin-top: 8rpx;
  color: var(--ui-text, #203047);
  font-size: 20px;
  font-weight: 900;
}

.preference-setup__desc {
  margin-top: 8rpx;
  color: #64748B;
  font-size: 23rpx;
  line-height: 1.5;
}

.preference-picker {
  display: flex;
  justify-content: space-between;
  margin-top: 22rpx;
  padding: 18rpx 0;
  border-top: 1px solid var(--ui-border, #dbe3ee);
  border-bottom: 1px solid var(--ui-border, #dbe3ee);
  color: var(--ui-text, #203047);
  font-size: 26rpx;
}

.preference-picker text:last-child {
  color: var(--ui-link, #285bc7);
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
  border: 1px solid var(--ui-border, #dbe3ee);
  border-radius: 999rpx;
  background: #ffffff;
  color: var(--ui-text, #203047);
  font-size: 24rpx;
  font-weight: 700;
}

.preference-chip--active {
  border-color: var(--ui-primary, #326be5);
  background: var(--ui-soft, #edf3ff);
  color: var(--ui-link, #285bc7);
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
  background: #EAF5FF;
  color: #2F7FD6;
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
  border: 1rpx solid #DCEAF7;
  border-radius: 12rpx;
  background: #ffffff;
  color: #5f6f83;
  font-size: 23rpx;
  font-weight: 800;
  text-align: center;
}

.trend-tab--active {
  border-color: #2F7FD6;
  background: #EAF5FF;
  color: #2F7FD6;
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
  background: linear-gradient(180deg, rgba(47, 127, 214, 0.14) 0%, rgba(47, 127, 214, 0.02) 100%);
  animation: trend-column-in 260ms ease-out both;
  transform-origin: bottom center;
}

.trend-chart__segment {
  position: absolute;
  height: 4rpx;
  border-radius: 999rpx;
  background: var(--ui-primary, #326be5);
  box-shadow: 0 4rpx 12rpx rgba(47, 127, 214, 0.14);
  transform-origin: left center;
  animation: trend-line-in 300ms ease-out both;
}

.trend-chart__point {
  position: absolute;
  width: 18rpx;
  height: 18rpx;
  margin-top: -9rpx;
  margin-left: -9rpx;
  border: 5rpx solid var(--ui-primary, #326be5);
  border-radius: 999rpx;
  background: #ffffff;
  box-shadow: 0 6rpx 18rpx rgba(47, 127, 214, 0.18);
  animation: trend-point-pop 260ms ease-out both;
}

.trend-chart__score {
  position: absolute;
  left: 50%;
  bottom: 22rpx;
  display: block;
  min-width: 58rpx;
  font-size: 20rpx;
  color: var(--ui-link, #285bc7);
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
  color: #64748B;
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
  color: var(--ui-text, #203047);
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
  background: var(--ui-primary, #326be5);
  transition: width 300ms ease-out;
}

.weakness-item__bar--weak {
  background: #cf1322;
}

.weakness-item__tip {
  display: block;
  margin-top: 10rpx;
  padding: 12rpx 14rpx;
  border-radius: 8rpx;
  background: #fff8eb;
  color: #6f4a12;
  font-size: 22rpx;
  line-height: 1.55;
}

.recommendation-status {
  padding: 28rpx 0;
  color: #64748B;
  font-size: 24rpx;
  text-align: center;
}

.recommendation-item {
  padding: 18rpx;
  border: 1px solid var(--ui-border, #dbe3ee);
  border-radius: 14rpx;
  background: var(--ui-bg, #f7f9fd);
  animation: motion-fade-up 220ms ease-out both;
}

.recommendation-item__head {
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: 12rpx;
  margin-bottom: 12rpx;
}

.recommendation-item__tag {
  flex: 0 0 auto;
  padding: 6rpx 14rpx;
  border-radius: 999rpx;
  background: var(--ui-soft, #edf3ff);
  color: var(--ui-link, #285bc7);
  font-size: 21rpx;
  font-weight: 800;
}

.recommendation-item__reason {
  min-width: 0;
  color: #64748B;
  font-size: 22rpx;
  line-height: 1.5;
}

.recommendation-item__stem {
  display: -webkit-box;
  overflow: hidden;
  color: var(--ui-text, #203047);
  font-size: 16px;
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
  color: var(--ui-muted, #596a80);
  font-size: 22rpx;
  font-weight: 700;
}

.recommendation-item__button {
  flex: 0 0 168rpx;
  min-height: 64rpx;
  font-size: 23rpx;
}

.learner-page.learner-home .jiangsu-entry {
  padding: 0 16px 16px;
  margin-bottom: 16px;
  border: 1px solid var(--ui-border, #dbe3ee);
  border-radius: 12px;
}

.jiangsu-entry__desc {
  display: block;
  margin-top: 8px;
  color: var(--ui-muted, #596a80);
  font-size: 14px;
  line-height: 1.5;
}

.jiangsu-grid { margin-top: 8px; }

.learner-page.learner-home .jiangsu-card {
  display: grid;
  grid-template-columns: minmax(0, 1fr) 20px;
  gap: 8px;
  align-items: center;
  width: 100%;
  min-height: 44px;
  padding: 12px 0;
  border: 0;
  border-top: 1px solid var(--ui-border, #dbe3ee);
  border-radius: 0;
  background: transparent;
  text-align: left;
  box-shadow: none;
}

.jiangsu-card__title,
.jiangsu-card__desc {
  display: block;
}

.jiangsu-card__title {
  color: var(--ui-text, #203047);
  font-size: 16px;
  font-weight: 600;
  line-height: 1.5;
}

.jiangsu-card__desc {
  margin-top: 4px;
  color: var(--ui-muted, #596a80);
  font-size: 14px;
  line-height: 1.5;
}

.jiangsu-card__arrow {
  color: var(--ui-muted, #596a80);
  font-size: 24px;
  line-height: 1;
}

.learner-home .record-card {
  display: flex;
  align-items: center;
  justify-content: space-between;
  width: 100%;
  min-height: 44px;
  margin-bottom: 8px;
  padding: 16px;
  text-align: left;
}

.record-card__main {
  min-width: 0;
  padding-right: 22rpx;
}

.record-card__title {
  display: -webkit-box;
  overflow: hidden;
  color: var(--ui-text, #203047);
  font-size: 16px;
  font-weight: 600;
  line-height: 1.5;
  -webkit-box-orient: vertical;
  -webkit-line-clamp: 2;
}

.record-card__meta {
  display: block;
  margin-top: 8px;
  color: var(--ui-muted, #596a80);
  font-size: 14px;
}

.record-card__action { display: block; margin-top: 8px; color: var(--ui-link, #285bc7); font-size: 14px; }

.learner-home .muted,
.preference-setup__kicker,
.preference-setup__desc,
.preference-picker,
.preference-chip,
.trend-chart__score,
.trend-chart__label,
.weakness-item__head,
.weakness-item__tip,
.recommendation-status,
.recommendation-item__tag,
.recommendation-item__reason,
.recommendation-item__footer {
  font-size: 14px;
}

.learner-home .muted,
.preference-setup__desc,
.recommendation-status,
.recommendation-item__reason,
.trend-chart__label {
  color: var(--ui-muted, #596a80);
}

.learner-home .primary-button,
.learner-home .secondary-button,
.preference-picker,
.preference-chip {
  min-height: 44px;
}

.preference-picker, .preference-chip { display: flex; align-items: center; }
.learner-home .recommendation-item__button { min-width: 96px; font-size: 14px; }
.learner-page.learner-home .primary-button { background: var(--ui-primary, #326be5); color: #ffffff; font-size: 16px; }
.learner-page.learner-home .secondary-button { color: var(--ui-link, #285bc7); border-color: var(--ui-border, #dbe3ee); }

@keyframes trend-column-in {
  from {
    opacity: 0;
    transform: scaleY(0.18);
  }
  to {
    opacity: 1;
    transform: scaleY(1);
  }
}

@keyframes trend-line-in {
  from {
    opacity: 0;
    transform: scaleX(0);
  }
  to {
    opacity: 1;
    transform: scaleX(1);
  }
}

@keyframes trend-point-pop {
  from {
    opacity: 0;
    transform: scale(0.62);
  }
  to {
    opacity: 1;
    transform: scale(1);
  }
}

@keyframes preference-mask-in {
  from {
    opacity: 0;
  }
  to {
    opacity: 1;
  }
}

@keyframes preference-panel-in {
  from {
    opacity: 0;
    transform: translateY(calc(-50% + 24rpx));
  }
  to {
    opacity: 1;
    transform: translateY(-50%);
  }
}
</style>
