<template>
  <view class="page">
    <text class="page-title">重点分析</text>
    <text class="page-desc">根据真实考试方向整理高频考点、能力重点和备考策略。</text>

    <view v-if="selectionTags.length" class="selection-card">
      <text v-for="tag in selectionTags" :key="tag" class="selection-tag">{{ tag }}</text>
    </view>

    <view v-if="targetedStore.focusLoading" class="card loading-card">
      <text class="loading-card__title">AI正在分析面试重点...</text>
      <text class="loading-card__desc">请稍候，系统正在根据省份和岗位整理核心考点。</text>
    </view>

    <view v-else-if="isEmptyFocus" class="card">
      <EmptyState title="暂无足够题库数据" :desc="targetedStore.focusData?.emptyMessage || '请选择已有真实题库的考试方向后再试。'" />
    </view>

    <view v-else-if="targetedStore.focusData" class="focus">
      <view v-if="coreFocus.length" class="card">
        <view class="section-head">
          <text class="section-title">核心能力权重</text>
        </view>
        <view v-for="item in coreFocus" :key="item.name" class="focus-row">
          <view class="focus-row__head">
            <text>{{ item.name }}</text>
            <text>{{ item.weight || 20 }}%</text>
          </view>
          <view class="focus-row__track">
            <view class="focus-row__bar" :style="{ width: `${item.weight || 20}%` }" />
          </view>
          <text class="focus-row__desc">{{ item.desc }}</text>
        </view>
      </view>

      <view v-if="highFreqTypes.length" class="card">
        <view class="section-head">
          <text class="section-title">高频题型</text>
        </view>
        <view v-for="item in highFreqTypes" :key="item.type" class="list-item">
          <text class="list-item__title">{{ item.type }} · {{ item.frequency || '中' }}</text>
          <text class="list-item__desc">{{ item.example || '结合岗位实际进行展开。' }}</text>
        </view>
      </view>

      <view v-if="strategy.length" class="card">
        <view class="section-head">
          <text class="section-title">备考策略</text>
        </view>
        <text v-for="item in strategy" :key="item" class="strategy-item">{{ item }}</text>
      </view>
    </view>
    <view v-else class="card">
      <EmptyState title="暂无分析结果" desc="请回到定向备面页选择方向后再试。" />
    </view>

    <button class="primary-button" :disabled="readonlyMode" :loading="targetedStore.focusLoading" @tap="loadFocus">刷新分析</button>
  </view>
</template>

<script setup>
import { computed } from 'vue'
import { onLoad } from '@dcloudio/uni-app'
import EmptyState from '../../components/EmptyState.vue'
import { useBillingStore } from '../../stores/billing'
import { useSubscriptionStore } from '../../stores/subscription'
import { useTargetedStore } from '../../stores/targeted'
import { useUserStore } from '../../stores/user'
import { hasPremiumAccess } from '../../utils/access'
import { hideLoading, requireLogin, showLoading, toast } from '../../utils/navigation'

const billingStore = useBillingStore()
const subscriptionStore = useSubscriptionStore()
const targetedStore = useTargetedStore()
const userStore = useUserStore()
const hasFullAccess = computed(() => hasPremiumAccess(userStore, billingStore, subscriptionStore))
const readonlyMode = computed(() => !hasFullAccess.value)
const coreFocus = computed(() => Array.isArray(targetedStore.focusData?.coreFocus) ? targetedStore.focusData.coreFocus : [])
const highFreqTypes = computed(() => Array.isArray(targetedStore.focusData?.highFreqTypes) ? targetedStore.focusData.highFreqTypes : [])
const strategy = computed(() => Array.isArray(targetedStore.focusData?.strategy) ? targetedStore.focusData.strategy : [])
const selectionTags = computed(() => {
  const payload = targetedStore.selectedTarget || targetedStore.selectionPayload || {}
  return [
    payload.examCategory,
    payload.examSubcategory,
    payload.system || payload.positionType || payload.portalTag,
    payload.targetName
  ].filter((item, index, array) => item && array.indexOf(item) === index)
})
const isEmptyFocus = computed(() => (
  targetedStore.focusData?.isFallback === true || Number(targetedStore.focusData?.questionCount || 0) <= 0
))

onLoad(async (options = {}) => {
  if (!requireLogin()) return
  applyRouteSelection(options)
  await refreshAccessState().catch(() => null)
  if (!targetedStore.hasSelection) {
    toast('请先选择考试方向')
    uni.navigateBack()
    return
  }
  if (!targetedStore.focusData) await loadFocus()
})

function applyRouteSelection(options = {}) {
  const payload = {}
  ;[
    'province',
    'position',
    'examCategory',
    'examSubcategory',
    'system',
    'positionType',
    'portalTag',
    'displayPortal',
    'targetCode',
    'targetName'
  ].forEach((key) => {
    const value = String(options[key] || '').trim()
    if (value) payload[key] = value
  })
  if (payload.targetCode || payload.examCategory || payload.targetName) {
    targetedStore.setTarget(payload)
    return
  }
  if (payload.province) targetedStore.setSelection(payload.province, payload.position || '')
}

async function refreshAccessState() {
  if (!userStore.isAuthenticated) return
  await Promise.allSettled([
    userStore.loadUserInfo(),
    subscriptionStore.refresh({ skipErrorHandler: true })
  ])
}

async function loadFocus() {
  if (readonlyMode.value) return
  if (!targetedStore.hasSelection) {
    toast('请先选择考试方向')
    uni.navigateBack()
    return
  }
  showLoading('分析中')
  try {
    await targetedStore.fetchFocusAnalysis()
  } catch (error) {
    toast(error?.message || '分析失败')
  } finally {
    hideLoading()
  }
}
</script>

<style scoped>
.focus-row {
  margin-bottom: 24rpx;
}

.selection-card {
  display: flex;
  flex-wrap: wrap;
  gap: 12rpx;
  margin: 8rpx 0 24rpx;
}

.selection-tag {
  padding: 8rpx 18rpx;
  border-radius: 999rpx;
  background: #eaf3fc;
  color: #1b5faa;
  font-size: 23rpx;
  font-weight: 600;
}

.focus-row:last-child {
  margin-bottom: 0;
}

.focus-row__head {
  display: flex;
  justify-content: space-between;
  color: #2a3648;
  font-size: 27rpx;
  font-weight: 700;
}

.focus-row__track {
  overflow: hidden;
  height: 12rpx;
  margin-top: 12rpx;
  border-radius: 999rpx;
  background: #edf2f7;
}

.focus-row__bar {
  height: 100%;
  border-radius: 999rpx;
  background: #1b5faa;
}

.focus-row__desc {
  display: block;
  margin-top: 10rpx;
  color: #6f7c8f;
  font-size: 24rpx;
  line-height: 1.6;
}

.list-item {
  padding: 20rpx 0;
  border-bottom: 1rpx solid #eef2f6;
}

.list-item:last-child {
  border-bottom: 0;
}

.list-item__title,
.list-item__desc,
.strategy-item {
  display: block;
}

.loading-card__title {
  display: block;
  color: #1a1a2e;
  font-size: 28rpx;
  font-weight: 700;
}

.loading-card__desc {
  display: block;
  margin-top: 10rpx;
  color: #6f7c8f;
  font-size: 24rpx;
  line-height: 1.6;
}

.list-item__title {
  color: #1a1a2e;
  font-size: 28rpx;
  font-weight: 700;
}

.list-item__desc,
.strategy-item {
  margin-top: 8rpx;
  color: #6f7c8f;
  font-size: 24rpx;
  line-height: 1.6;
}

.strategy-item {
  padding: 14rpx 0;
}
</style>
