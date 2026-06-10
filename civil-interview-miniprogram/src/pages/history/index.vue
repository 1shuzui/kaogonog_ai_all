<!--
小程序历史记录页承接账号维度的练习回看，因此必须在用户主动登录后再请求个人数据，避免审核认为首页强制授权。
筛选条件只影响历史查询范围，不能在端侧伪造成绩、维度或题目摘要；结果详情仍以后端评分记录为准。

@param: 无；页面通过 Pinia 历史记录状态、用户身份状态和筛选控件组合查询条件。
@return: 渲染练习记录、分页入口和空态提示，登录拦截交给统一导航工具处理。
@raises: 不主动抛业务异常；接口失败、未登录和权限不足由请求层或页面提示承接。
-->
<template>
  <view class="page">
    <view class="page-head">
      <button class="secondary-button page-head__back" @tap="goBack">返回</button>
      <view>
        <text class="page-title">历史记录</text>
        <text class="page-desc">回看每次练习的得分、题目和维度表现。</text>
      </view>
    </view>

    <view class="card filter-card">
      <picker :range="provinceNames" :value="provinceIndex" @change="onProvinceChange">
        <view class="filter-row">
          <text>省份</text>
          <text class="filter-row__value">{{ selectedProvinceName }}</text>
        </view>
      </picker>
      <view class="date-grid">
        <picker mode="date" :value="startDate" @change="onStartDateChange">
          <view class="date-cell">
            <text>开始日期</text>
            <text>{{ startDate || '不限' }}</text>
          </view>
        </picker>
        <picker mode="date" :value="endDate" @change="onEndDateChange">
          <view class="date-cell">
            <text>结束日期</text>
            <text>{{ endDate || '不限' }}</text>
          </view>
        </picker>
      </view>
      <view class="filter-actions">
        <button class="secondary-button" @tap="resetFilters">重置</button>
        <button class="primary-button" :loading="historyStore.loading" @tap="refreshRecords">筛选</button>
      </view>
    </view>

    <view v-if="historyStore.records.length">
      <view
        v-for="record in historyStore.records"
        :key="record.examId"
        class="history-card card"
        @tap="openResult(record)"
      >
        <view class="history-card__main">
          <text class="history-card__title">{{ record.questionSummary || '全真模拟练习' }}</text>
          <text class="history-card__meta">{{ formatDate(record.completedAt || record.date) }} · {{ record.questionCount || 1 }} 题</text>
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
import { computed, ref } from 'vue'
import { onShow } from '@dcloudio/uni-app'
import EmptyState from '../../components/EmptyState.vue'
import ScoreRing from '../../components/ScoreRing.vue'
import { useHistoryStore } from '../../stores/history'
import { useUserStore } from '../../stores/user'
import { formatDate } from '../../utils/format'
import { PROVINCES } from '../../utils/constants'
import { requireLogin } from '../../utils/navigation'

const historyStore = useHistoryStore()
const userStore = useUserStore()
const selectedProvince = ref('all')
const startDate = ref('')
const endDate = ref('')
const provinceOptions = computed(() => [
  { code: 'all', name: '全部省份' },
  ...(userStore.provinces.length ? userStore.provinces : PROVINCES)
])
const provinceNames = computed(() => provinceOptions.value.map((item) => item.name))
const provinceIndex = computed(() => Math.max(0, provinceOptions.value.findIndex((item) => item.code === selectedProvince.value)))
const selectedProvinceName = computed(() => provinceOptions.value[provinceIndex.value]?.name || '全部省份')

onShow(async () => {
  if (!requireLogin()) return
  await userStore.loadProvinces().catch(() => null)
  if (!historyStore.records.length) refreshRecords()
})

function queryParams(page = 1) {
  return {
    current: page,
    page,
    province: selectedProvince.value === 'all' ? '' : selectedProvince.value,
    startDate: startDate.value,
    endDate: endDate.value
  }
}

function refreshRecords() {
  historyStore.fetchRecords(queryParams(1))
}

async function loadMore() {
  await historyStore.fetchMore(queryParams(historyStore.pagination.current + 1))
}

function onProvinceChange(event) {
  const selected = provinceOptions.value[Number(event.detail.value)]
  selectedProvince.value = selected?.code || 'all'
  refreshRecords()
}

function onStartDateChange(event) {
  startDate.value = event.detail.value || ''
  refreshRecords()
}

function onEndDateChange(event) {
  endDate.value = event.detail.value || ''
  refreshRecords()
}

function resetFilters() {
  selectedProvince.value = 'all'
  startDate.value = ''
  endDate.value = ''
  refreshRecords()
}

function goBack() {
  const pages = typeof getCurrentPages === 'function' ? getCurrentPages() : []
  if (pages.length > 1) {
    uni.navigateBack()
    return
  }
  uni.switchTab({ url: '/pages/profile/index' })
}

function openResult(record) {
  uni.navigateTo({ url: `/pages/result/index?examId=${encodeURIComponent(record.examId)}` })
}
</script>

<style scoped>
.page-head {
  display: flex;
  align-items: flex-start;
  gap: 18rpx;
  margin-bottom: 18rpx;
}

.page-head__back {
  flex: 0 0 auto;
  width: 132rpx;
  margin: 0;
}

.history-card {
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.filter-card {
  padding-bottom: 22rpx;
}

.filter-row {
  display: flex;
  justify-content: space-between;
  padding: 16rpx 0;
  border-bottom: 1rpx solid #eef2f6;
  color: #2a3648;
  font-size: 27rpx;
}

.filter-row__value {
  color: #2F7FD6;
  font-weight: 700;
}

.date-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 14rpx;
  margin-top: 18rpx;
}

.date-cell {
  padding: 18rpx;
  border-radius: 14rpx;
  background: #f6f8fb;
}

.date-cell text {
  display: block;
  color: #64748B;
  font-size: 23rpx;
}

.date-cell text:last-child {
  margin-top: 8rpx;
  color: #172033;
  font-size: 26rpx;
  font-weight: 800;
}

.filter-actions {
  display: grid;
  grid-template-columns: 170rpx minmax(0, 1fr);
  gap: 14rpx;
  margin-top: 18rpx;
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
  color: #64748B;
  font-size: 23rpx;
}
</style>
