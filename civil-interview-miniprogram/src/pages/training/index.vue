<template>
  <view class="page page--tab">
    <text class="page-title">专项训练</text>
    <text class="page-desc">按题型集中训练，逐个突破短板。</text>

    <view class="training-list">
      <view
        v-for="category in TRAINING_CATEGORIES"
        :key="category.key"
        class="training-card card"
        @tap="openDimension(category)"
      >
        <view class="training-card__icon" :style="{ background: category.tone }">{{ category.icon }}</view>
        <view class="training-card__copy">
          <text class="training-card__title">{{ category.name }}</text>
          <text class="training-card__desc">{{ category.tip }}</text>
          <text class="training-card__meta">{{ progressText(category.key) }}</text>
        </view>
        <text class="training-card__arrow">›</text>
      </view>
    </view>
  </view>
</template>

<script setup>
import { onShow } from '@dcloudio/uni-app'
import { useTrainingStore } from '../../stores/training'
import { TRAINING_CATEGORIES } from '../../utils/constants'
import { requireLogin } from '../../utils/navigation'

const trainingStore = useTrainingStore()

onShow(() => {
  requireLogin()
})

function progressText(key) {
  const progress = trainingStore.getDimensionProgress(key)
  if (!progress.attempts) return '尚未练习'
  return `练习 ${progress.attempts} 次 · 最佳 ${progress.bestScore} 分`
}

function openDimension(category) {
  uni.navigateTo({ url: `/pages/training/dimension?key=${encodeURIComponent(category.key)}` })
}
</script>

<style scoped>
.training-card {
  display: grid;
  grid-template-columns: 92rpx minmax(0, 1fr) 38rpx;
  gap: 20rpx;
  align-items: center;
}

.training-card__icon {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 92rpx;
  height: 92rpx;
  border-radius: 18rpx;
  color: #1b5faa;
  font-size: 34rpx;
  font-weight: 900;
}

.training-card__title,
.training-card__desc,
.training-card__meta {
  display: block;
}

.training-card__title {
  color: #1a1a2e;
  font-size: 31rpx;
  font-weight: 800;
}

.training-card__desc {
  margin-top: 6rpx;
  color: #6f7c8f;
  font-size: 23rpx;
  line-height: 1.5;
}

.training-card__meta {
  margin-top: 8rpx;
  color: #1b5faa;
  font-size: 23rpx;
}

.training-card__arrow {
  color: #8c8c8c;
  font-size: 46rpx;
  line-height: 1;
}
</style>
