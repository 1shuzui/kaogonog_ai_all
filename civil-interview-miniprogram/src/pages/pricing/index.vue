<template>
  <view class="page">
    <text class="page-title">套餐中心</text>
    <text class="page-desc">开通结果以后端订单和微信支付通知为准，支付完成后会自动同步权益。</text>

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
        <text class="plan-card__price">¥99</text>
        <text class="plan-card__desc">适合短期冲刺，解锁完整模考、定向备面、专项训练。</text>
      </view>
      <button class="primary-button" :loading="loadingPlan === 'hourly'" :disabled="!!loadingPlan" @tap="activate('hourly')">立即开通</button>
    </view>

    <view class="plan-card card">
      <view>
        <text class="plan-card__title">包月套餐</text>
        <text class="plan-card__price">¥299</text>
        <text class="plan-card__desc">适合系统备考，当前周期内不限次数练习。</text>
      </view>
      <button class="primary-button" :loading="loadingPlan === 'monthly'" :disabled="!!loadingPlan" @tap="activate('monthly')">立即开通</button>
    </view>
  </view>
</template>

<script setup>
import { ref } from 'vue'
import { createPaymentOrder, getPaymentOrder, mockWechatPaymentCallback } from '../../api/payment'
import { useBillingStore } from '../../stores/billing'
import { useUserStore } from '../../stores/user'
import { toast } from '../../utils/navigation'

const billingStore = useBillingStore()
const userStore = useUserStore()
const loadingPlan = ref('')
const WECHAT_APPID = import.meta.env.VITE_WECHAT_APPID || 'wxa31c6e32dfa4b178'

const PACKAGE_BY_PLAN = {
  hourly: 'trial_3h',
  monthly: 'monthly_1h_day'
}

function createIdempotencyKey(plan) {
  return `mini_${plan}_${Date.now()}_${Math.random().toString(36).slice(2, 8)}`
}

function loginForPayCode() {
  return new Promise((resolve, reject) => {
    uni.login({
      provider: 'weixin',
      success(res) {
        if (res.code) resolve(res.code)
        else reject(new Error('微信登录未返回 code'))
      },
      fail(err) {
        reject(new Error(err?.errMsg || '微信登录失败'))
      }
    })
  })
}

function requestWechatPayment(payParams = {}) {
  return new Promise((resolve, reject) => {
    uni.requestPayment({
      provider: 'wxpay',
      timeStamp: String(payParams.timeStamp || ''),
      nonceStr: payParams.nonceStr || '',
      package: payParams.package || '',
      signType: payParams.signType || 'RSA',
      paySign: payParams.paySign || '',
      success: resolve,
      fail(err) {
        reject(new Error(err?.errMsg || '微信支付未完成'))
      }
    })
  })
}

async function waitOrderPaid(orderNo) {
  for (let index = 0; index < 5; index += 1) {
    const order = await getPaymentOrder(orderNo)
    if (order?.status === 'paid') return order
    await new Promise((resolve) => setTimeout(resolve, 1200))
  }
  return null
}

async function activate(plan) {
  if (!PACKAGE_BY_PLAN[plan] || loadingPlan.value) return
  loadingPlan.value = plan
  try {
    const code = await loginForPayCode()
    const order = await createPaymentOrder({
      packageCode: PACKAGE_BY_PLAN[plan],
      payChannel: 'wechat',
      scene: 'mini_program',
      appId: WECHAT_APPID,
      code,
      idempotencyKey: createIdempotencyKey(plan)
    })

    if (order.payParams?.mode === 'mock') {
      if (import.meta.env.PROD) {
        toast('服务器仍返回测试支付参数，请检查后端微信支付配置')
        return
      }
      await mockWechatPaymentCallback({
        orderNo: order.orderNo,
        status: 'paid',
        amountTotal: Math.round(Number(order.amount || 0) * 100),
        callbackPayload: {
          source: 'mini_program_pricing_page',
          packageCode: order.packageCode
        }
      })
      await userStore.loadUserInfo()
      toast('开通成功', 'success')
      return
    }

    await requestWechatPayment(order.payParams?.miniProgramPay || {})
    const paidOrder = await waitOrderPaid(order.orderNo)
    await userStore.loadUserInfo()
    toast(paidOrder ? '支付成功，权益已同步' : '支付已提交，权益同步中', 'success')
  } catch (error) {
    toast(error?.message || '支付未完成，请稍后重试')
  } finally {
    loadingPlan.value = ''
  }
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
