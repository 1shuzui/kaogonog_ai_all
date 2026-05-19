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

    <view class="quick-grid">
      <button class="primary-button" @tap="goPrepare">开始模考</button>
      <button class="secondary-button" @tap="goPricing">套餐中心</button>
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

    <view class="section-head">
      <text class="section-title">近期练习</text>
      <text class="muted" @tap="goHistory">查看全部</text>
    </view>

    <view v-if="recentRecords.length">
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
    <view v-else class="card">
      <EmptyState title="暂无练习记录" desc="完成一次模考后，这里会展示近期得分和趋势。" mark="0" />
    </view>

    <view v-if="historyStore.stats?.dimensionAverages?.length" class="card">
      <view class="section-head">
        <text class="section-title">能力概览</text>
      </view>
      <DimensionBars :dimensions="historyStore.stats.dimensionAverages" />
    </view>
  </view>
</template>

<script setup>
import { computed } from 'vue'
import { onPullDownRefresh, onShow } from '@dcloudio/uni-app'
import DimensionBars from '../../components/DimensionBars.vue'
import EmptyState from '../../components/EmptyState.vue'
import ScoreRing from '../../components/ScoreRing.vue'
import StatGrid from '../../components/StatGrid.vue'
import { useHistoryStore } from '../../stores/history'
import { useUserStore } from '../../stores/user'
import { formatDate } from '../../utils/format'
import { JIANGSU_JOB_CATEGORIES } from '../../utils/jiangsuJobs'
import { requireLogin } from '../../utils/navigation'

const historyStore = useHistoryStore()
const userStore = useUserStore()
const jiangsuJobs = JIANGSU_JOB_CATEGORIES

const showJiangsuEntry = computed(() => userStore.selectedProvince === 'jiangsu')
const hasFullAccess = computed(() => (
  userStore.isAdmin
  || userStore.userInfo?.billing?.isPaid === true
  || userStore.userInfo?.permissions?.canAccessPremiumModules === true
))
const recentRecords = computed(() => (historyStore.records || []).slice(0, 3))
const statItems = computed(() => [
  { label: '练习次数', value: historyStore.stats?.totalExams || 0 },
  { label: '最高分', value: historyStore.bestScore || 0 },
  { label: '薄弱维度', value: historyStore.weakestDimension || '暂无' }
])

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
}

async function goPrepare() {
  await userStore.loadUserInfo().catch(() => null)
  uni.navigateTo({ url: hasFullAccess.value ? '/pages/exam/prepare' : '/pages/exam/prepare?trial=1' })
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
  grid-template-columns: 1.3fr 1fr;
  gap: 16rpx;
  margin-bottom: 28rpx;
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
