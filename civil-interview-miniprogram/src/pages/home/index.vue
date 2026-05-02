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
          <text class="record-card__title">{{ record.questionSummary || '模拟面试练习' }}</text>
          <text class="record-card__meta">{{ formatDate(record.date) }} · {{ record.questionCount || 1 }} 题</text>
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
import { requireLogin } from '../../utils/navigation'

const historyStore = useHistoryStore()
const userStore = useUserStore()

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

function goPrepare() {
  uni.navigateTo({ url: '/pages/exam/prepare' })
}

function goPricing() {
  uni.navigateTo({ url: '/pages/pricing/index' })
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
