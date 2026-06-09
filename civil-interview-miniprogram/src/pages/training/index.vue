<!--
这个小程序训练首页展示题型分类入口，未登录用户可以看入口，生成真实题目前再登录。

@param: 无；页面运行时从 props、路由参数、Pinia 状态和用户点击中拿数据。
@return: 渲染当前业务界面，并把按钮、表单或跳转事件交给既有流程处理。
@raises: 不主动抛业务异常；接口失败、未登录和权限不足由请求层或页面提示承接。
-->
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
import { useTrainingStore } from '../../stores/training'
import { TRAINING_CATEGORIES } from '../../utils/constants'

const trainingStore = useTrainingStore()

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
  color: #2F7FD6;
  font-size: 43rpx;
  font-weight: 900;
  line-height: 1;
}

.training-card__title,
.training-card__desc,
.training-card__meta {
  display: block;
}

.training-card__title {
  color: #172033;
  font-size: 31rpx;
  font-weight: 800;
}

.training-card__desc {
  margin-top: 6rpx;
  color: #64748B;
  font-size: 23rpx;
  line-height: 1.5;
}

.training-card__meta {
  margin-top: 8rpx;
  color: #2F7FD6;
  font-size: 23rpx;
}

.training-card__arrow {
  color: #8c8c8c;
  font-size: 46rpx;
  line-height: 1;
}
</style>
