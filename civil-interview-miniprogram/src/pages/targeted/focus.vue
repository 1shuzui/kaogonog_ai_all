<template>
  <view class="page">
    <text class="page-title">重点分析</text>
    <text class="page-desc">根据省份和岗位系统整理高频考点、能力重点和备考策略。</text>

    <view v-if="targetedStore.focusData" class="focus">
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

    <button class="primary-button" :loading="targetedStore.focusLoading" @tap="loadFocus">刷新分析</button>
  </view>
</template>

<script setup>
import { computed } from 'vue'
import { onLoad } from '@dcloudio/uni-app'
import EmptyState from '../../components/EmptyState.vue'
import { useTargetedStore } from '../../stores/targeted'
import { hideLoading, requireLogin, showLoading, toast } from '../../utils/navigation'

const targetedStore = useTargetedStore()
const coreFocus = computed(() => Array.isArray(targetedStore.focusData?.coreFocus) ? targetedStore.focusData.coreFocus : [])
const highFreqTypes = computed(() => Array.isArray(targetedStore.focusData?.highFreqTypes) ? targetedStore.focusData.highFreqTypes : [])
const strategy = computed(() => Array.isArray(targetedStore.focusData?.strategy) ? targetedStore.focusData.strategy : [])

onLoad(() => {
  if (!requireLogin()) return
  if (targetedStore.hasSelection && !targetedStore.focusData) loadFocus()
})

async function loadFocus() {
  if (!targetedStore.hasSelection) {
    toast('请先选择省份和岗位系统')
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
