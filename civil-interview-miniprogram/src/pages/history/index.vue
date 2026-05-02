<template>
  <view class="page">
    <text class="page-title">历史记录</text>
    <text class="page-desc">回看每次练习的得分、题目和维度表现。</text>

    <view v-if="historyStore.records.length">
      <view
        v-for="record in historyStore.records"
        :key="record.examId"
        class="history-card card"
        @tap="openResult(record)"
      >
        <view class="history-card__main">
          <text class="history-card__title">{{ record.questionSummary || '模拟面试练习' }}</text>
          <text class="history-card__meta">{{ formatDate(record.date) }} · {{ record.questionCount || 1 }} 题</text>
        </view>
        <ScoreRing :score="record.totalScore || 0" :max-score="record.maxScore || 100" size="small" />
      </view>
    </view>
    <view v-else class="card">
      <EmptyState title="暂无历史记录" desc="完成练习后可在这里查看评分报告。" />
    </view>

    <button
      v-if="historyStore.pagination.total > historyStore.records.length"
      class="secondary-button"
      :loading="historyStore.loading"
      @tap="loadMore"
    >
      加载更多
    </button>
  </view>
</template>

<script setup>
import { onShow } from '@dcloudio/uni-app'
import EmptyState from '../../components/EmptyState.vue'
import ScoreRing from '../../components/ScoreRing.vue'
import { useHistoryStore } from '../../stores/history'
import { formatDate } from '../../utils/format'
import { requireLogin } from '../../utils/navigation'

const historyStore = useHistoryStore()

onShow(() => {
  if (!requireLogin()) return
  if (!historyStore.records.length) historyStore.fetchRecords({ page: 1 })
})

async function loadMore() {
  const previous = [...historyStore.records]
  await historyStore.fetchRecords({ page: historyStore.pagination.current + 1 })
  historyStore.records = [...previous, ...historyStore.records]
}

function openResult(record) {
  uni.navigateTo({ url: `/pages/result/index?examId=${encodeURIComponent(record.examId)}` })
}
</script>

<style scoped>
.history-card {
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.history-card__main {
  min-width: 0;
  padding-right: 22rpx;
}

.history-card__title {
  display: -webkit-box;
  overflow: hidden;
  color: #1f2b3d;
  font-size: 29rpx;
  font-weight: 600;
  line-height: 1.5;
  -webkit-box-orient: vertical;
  -webkit-line-clamp: 2;
}

.history-card__meta {
  display: block;
  margin-top: 10rpx;
  color: #6f7c8f;
  font-size: 23rpx;
}
</style>
