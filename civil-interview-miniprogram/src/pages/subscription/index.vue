<template>
  <view class="page">
    <view class="page-head">
      <view>
        <text class="page-title">订阅权益</text>
        <text class="page-desc">剩余额度、每日额度和访问权限与后端实时同步。</text>
      </view>
      <button class="secondary-button page-head__button" :loading="subscriptionStore.loading" @tap="refresh">刷新</button>
    </view>

    <view class="status-card card">
      <text class="status-card__label">当前套餐</text>
      <text class="status-card__title">{{ status.planName || planTitle }}</text>
      <text class="status-card__desc">{{ statusDesc }}</text>
    </view>

    <view class="card">
      <view class="section-head">
        <text class="section-title">额度</text>
        <text class="muted">{{ status.status || 'trial' }}</text>
      </view>
      <view class="metric-grid">
        <view class="metric">
          <text class="metric__value">{{ status.remainingMinutes }}</text>
          <text class="metric__label">剩余分钟</text>
        </view>
        <view class="metric">
          <text class="metric__value">{{ status.remainingDailyMinutes }}</text>
          <text class="metric__label">今日可用</text>
        </view>
        <view class="metric">
          <text class="metric__value">{{ status.usedMinutes }}</text>
          <text class="metric__label">累计使用</text>
        </view>
      </view>
      <view class="detail-row">
        <text>到期时间</text>
        <text>{{ formatDate(status.expiresAt) || '-' }}</text>
      </view>
      <view class="detail-row">
        <text>试用状态</text>
        <text>{{ status.trialCompleted ? '已完成试用' : '可试用' }}</text>
      </view>
      <view v-if="status.entitlements?.length" class="entitlement-list">
        <view v-for="item in status.entitlements" :key="item.id || item.sourceOrderNo" class="entitlement-item">
          <text class="entitlement-item__title">{{ item.planName }}</text>
          <text class="entitlement-item__desc">剩余 {{ item.remainingMinutes }} 分钟{{ item.expiresAt ? ` | 到期 ${formatDate(item.expiresAt)}` : '' }}</text>
        </view>
      </view>
    </view>

    <view class="card">
      <view class="section-head">
        <text class="section-title">访问检查</text>
        <text class="muted">{{ access?.mode || 'practice' }}</text>
      </view>
      <view class="access-row">
        <button class="secondary-button" @tap="checkAccess('practice')">自由练习</button>
        <button class="secondary-button" @tap="checkAccess('mock')">模拟面试</button>
      </view>
      <text class="access-result" :class="{ 'access-result--ok': access?.allowed }">
        {{ accessText }}
      </text>
    </view>

    <button class="primary-button" @tap="goPricing">开通或续费</button>
  </view>
</template>

<script setup>
import { computed } from 'vue'
import { onShow } from '@dcloudio/uni-app'
import { useSubscriptionStore } from '../../stores/subscription'
import { formatDate } from '../../utils/format'
import { requireLogin, toast } from '../../utils/navigation'

const subscriptionStore = useSubscriptionStore()
const status = computed(() => subscriptionStore.status)
const access = computed(() => subscriptionStore.access)
const planTitle = computed(() => status.value.planType === 'trial' ? '试用版' : '已开通套餐')
const statusDesc = computed(() => {
  if (!status.value.canUse) return '当前权益不可用'
  return status.value.stacked ? `当前可进入练习与模考，已叠加 ${status.value.activePlanCount} 项权益` : '当前可进入练习与模考'
})
const accessText = computed(() => {
  if (!access.value) return '尚未检查'
  if (access.value.allowed) return `允许进入，剩余 ${access.value.remainingMinutes || 0} 分钟`
  return access.value.reason || '当前暂不可用'
})

onShow(() => {
  if (!requireLogin()) return
  refresh()
})

async function refresh() {
  try {
    await subscriptionStore.refresh({ skipErrorHandler: true })
    await checkAccess('practice', true)
  } catch (error) {
    toast(error?.message || '订阅状态加载失败')
  }
}

async function checkAccess(mode, silent = false) {
  try {
    await subscriptionStore.check(mode, { skipErrorHandler: true })
  } catch (error) {
    if (!silent) toast(error?.message || '访问检查失败')
  }
}

function goPricing() {
  uni.navigateTo({ url: '/pages/pricing/index' })
}
</script>

<style scoped>
.page-head {
  display: grid;
  grid-template-columns: minmax(0, 1fr) 140rpx;
  gap: 18rpx;
  align-items: start;
}

.page-head__button {
  min-height: 76rpx;
}

.status-card {
  background: #15477a;
  color: #ffffff;
}

.status-card__label,
.status-card__title,
.status-card__desc {
  display: block;
}

.status-card__label {
  opacity: 0.82;
  font-size: 24rpx;
}

.status-card__title {
  margin-top: 10rpx;
  font-size: 42rpx;
  font-weight: 800;
}

.status-card__desc {
  margin-top: 10rpx;
  opacity: 0.86;
  font-size: 25rpx;
}

.metric-grid {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 14rpx;
}

.metric {
  padding: 20rpx 12rpx;
  border-radius: 14rpx;
  background: #f6f8fb;
  text-align: center;
}

.metric__value,
.metric__label {
  display: block;
}

.metric__value {
  color: #1b5faa;
  font-size: 34rpx;
  font-weight: 900;
}

.metric__label {
  margin-top: 6rpx;
  color: #6f7c8f;
  font-size: 22rpx;
}

.detail-row {
  display: flex;
  justify-content: space-between;
  padding: 18rpx 0 0;
  color: #2a3648;
  font-size: 25rpx;
}

.detail-row text:last-child {
  color: #1a1a2e;
  font-weight: 700;
}

.entitlement-list {
  display: grid;
  gap: 12rpx;
  margin-top: 18rpx;
}

.entitlement-item {
  padding: 16rpx;
  border: 1rpx solid #e5edf7;
  border-radius: 14rpx;
  background: #f8fbff;
}

.entitlement-item__title,
.entitlement-item__desc {
  display: block;
}

.entitlement-item__title {
  color: #1a1a2e;
  font-size: 25rpx;
  font-weight: 800;
}

.entitlement-item__desc {
  margin-top: 6rpx;
  color: #6f7c8f;
  font-size: 22rpx;
}

.access-row {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 14rpx;
}

.access-result {
  display: block;
  margin-top: 18rpx;
  color: #cf1322;
  font-size: 25rpx;
  font-weight: 700;
}

.access-result--ok {
  color: #389e0d;
}
</style>
