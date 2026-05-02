<template>
  <view class="page">
    <text class="page-title">套餐中心</text>
    <text class="page-desc">当前小程序端提供与网页端一致的本地演示开通能力，后续可接入真实支付。</text>

    <view class="pricing-status card">
      <text class="pricing-status__label">当前套餐</text>
      <text class="pricing-status__title">{{ billingStore.plan.title }}</text>
      <text class="pricing-status__desc">{{ billingStore.plan.status }}</text>
    </view>

    <view class="plan-card card">
      <view>
        <text class="plan-card__title">试用版</text>
        <text class="plan-card__price">¥0</text>
        <text class="plan-card__desc">体验 1 道引导题，熟悉录音与评分流程。</text>
      </view>
      <button class="secondary-button" @tap="startTrial">开始试用</button>
    </view>

    <view class="plan-card card">
      <view>
        <text class="plan-card__title">按时套餐</text>
        <text class="plan-card__price">¥19.9</text>
        <text class="plan-card__desc">适合短期冲刺，解锁完整模考、定向备面、专项训练。</text>
      </view>
      <button class="primary-button" @tap="activate('hourly')">立即开通</button>
    </view>

    <view class="plan-card card">
      <view>
        <text class="plan-card__title">包月套餐</text>
        <text class="plan-card__price">¥59.9</text>
        <text class="plan-card__desc">适合系统备考，当前周期内不限次数练习。</text>
      </view>
      <button class="primary-button" @tap="activate('monthly')">立即开通</button>
    </view>
  </view>
</template>

<script setup>
import { useBillingStore } from '../../stores/billing'
import { toast } from '../../utils/navigation'

const billingStore = useBillingStore()

function activate(plan) {
  billingStore.activate(plan)
  toast('开通成功', 'success')
}

function startTrial() {
  uni.navigateTo({ url: '/pages/exam/prepare?trial=1' })
}
</script>

<style scoped>
.pricing-status {
  background: linear-gradient(135deg, #15477a 0%, #1b5faa 66%, #5fa0e8 100%);
  color: #ffffff;
}

.pricing-status__label,
.pricing-status__title,
.pricing-status__desc,
.plan-card__title,
.plan-card__price,
.plan-card__desc {
  display: block;
}

.pricing-status__label {
  opacity: 0.82;
  font-size: 24rpx;
}

.pricing-status__title {
  margin-top: 10rpx;
  font-size: 42rpx;
  font-weight: 800;
}

.pricing-status__desc {
  margin-top: 10rpx;
  opacity: 0.86;
  font-size: 25rpx;
}

.plan-card {
  display: grid;
  grid-template-columns: minmax(0, 1fr) 190rpx;
  gap: 20rpx;
  align-items: center;
}

.plan-card__title {
  color: #1a1a2e;
  font-size: 32rpx;
  font-weight: 800;
}

.plan-card__price {
  margin-top: 8rpx;
  color: #1b5faa;
  font-size: 38rpx;
  font-weight: 900;
}

.plan-card__desc {
  margin-top: 8rpx;
  color: #6f7c8f;
  font-size: 24rpx;
  line-height: 1.6;
}
</style>
