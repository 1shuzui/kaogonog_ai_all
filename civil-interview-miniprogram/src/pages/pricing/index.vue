<template>
  <view class="page">
    <text class="page-title">套餐中心</text>
    <text class="page-desc">小程序内虚拟权益购买使用微信官方虚拟支付能力，支付完成后会自动同步权益。</text>

    <view class="pricing-status card">
      <text class="pricing-status__label">当前套餐</text>
      <text class="pricing-status__title">{{ billingStore.plan.title }}</text>
      <text class="pricing-status__desc">{{ billingStore.plan.status }}</text>
    </view>

    <view class="plan-card card">
      <view>
        <text class="plan-card__title">试用版</text>
        <text class="plan-card__price">¥0</text>
        <text class="plan-card__desc">体验 1 道引导题，熟悉录音/录像提交、AI评分和结果页流程。</text>
        <view class="feature-list">
          <text>一次完整试用流程</text>
          <text>结果页维度展示</text>
          <text>适合先检测设备与网络</text>
        </view>
      </view>
      <button class="secondary-button" @tap="startTrial">开始试用</button>
    </view>

    <view class="plan-card card">
      <view>
        <text class="plan-card__title">按时套餐</text>
        <text class="plan-card__price">¥0.01</text>
        <text class="plan-card__desc">总计 3 小时训练时长，适合短期冲刺，按实际训练消耗。</text>
        <view class="feature-list">
          <text>完整全真模拟</text>
          <text>定向备面与专项训练</text>
          <text>可与已有权益叠加</text>
          <text>历史报告、收藏题和低分错题复盘</text>
        </view>
      </view>
      <button class="primary-button" :loading="loadingPlan === 'hourly'" :disabled="!!loadingPlan" @tap="activate('hourly')">立即开通</button>
    </view>

    <view class="plan-card card">
      <view>
        <text class="plan-card__title">包月套餐</text>
        <text class="plan-card__price">¥0.01</text>
        <text class="plan-card__desc">30 天有效期，每日 1 小时训练额度，适合稳定推进备考计划。</text>
        <view class="feature-list">
          <text>每日额度自动刷新</text>
          <text>完整付费训练模块</text>
          <text>续费和按时包可叠加汇总</text>
          <text>错题收藏、历史复盘和智能推荐</text>
        </view>
      </view>
      <button class="primary-button" :loading="loadingPlan === 'monthly'" :disabled="!!loadingPlan" @tap="activate('monthly')">立即开通</button>
    </view>

    <view class="card pricing-note">
      <text>支付说明</text>
      <text>当前测试金额统一为 ¥0.01。付费权益允许叠加，系统会优先消耗更早到期的余额；支付成功后以小程序虚拟支付结果、后端订单和账户权益同步结果为准。</text>
    </view>
  </view>
</template>

<script setup>
import { ref } from 'vue'
import { confirmVirtualPaymentOrder, createPaymentOrder, getPaymentOrder } from '../../api/payment'
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

function compareVersion(versionA = '', versionB = '') {
  const a = String(versionA || '').split('.').map((item) => Number(item) || 0)
  const b = String(versionB || '').split('.').map((item) => Number(item) || 0)
  const length = Math.max(a.length, b.length)
  for (let index = 0; index < length; index += 1) {
    const diff = (a[index] || 0) - (b[index] || 0)
    if (diff !== 0) return diff
  }
  return 0
}

function canUseWechatVirtualPayment() {
  if (typeof wx === 'undefined' || typeof wx.requestVirtualPayment !== 'function') return false
  const sdkVersion = wx.getSystemInfoSync?.().SDKVersion || ''
  return compareVersion(sdkVersion, '2.19.2') >= 0 || wx.canIUse?.('requestVirtualPayment') === true
}

function parseVirtualPaySignData(signData) {
  if (typeof signData !== 'string' || !signData.trim()) {
    throw new Error('小程序虚拟支付参数不完整：缺少 signData')
  }
  try {
    return JSON.parse(signData)
  } catch {
    throw new Error('小程序虚拟支付参数格式错误：signData 必须为 JSON 字符串')
  }
}

function validateWechatVirtualPayParams(payParams = {}) {
  const requiredFields = ['signData', 'mode', 'paySig', 'signature']
  const missing = requiredFields.filter((field) => !payParams[field])
  if (missing.length) {
    throw new Error(`小程序虚拟支付参数不完整：缺少 ${missing.join('、')}`)
  }

  const signData = parseVirtualPaySignData(payParams.signData)
  const requiredSignDataFields = ['offerId', 'buyQuantity', 'currencyType', 'outTradeNo', 'attach']
  const missingSignData = requiredSignDataFields.filter((field) => signData[field] === undefined || signData[field] === '')
  if (missingSignData.length) {
    throw new Error(`小程序虚拟支付 signData 不完整：缺少 ${missingSignData.join('、')}`)
  }
  if (signData.currencyType !== 'CNY') {
    throw new Error('小程序虚拟支付仅支持 CNY 币种')
  }
  if (payParams.mode === 'short_series_goods' && (!signData.productId || !signData.goodsPrice)) {
    throw new Error('小程序虚拟支付道具直购参数不完整')
  }
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

function requestWechatVirtualPayment(payParams = {}) {
  return new Promise((resolve, reject) => {
    if (!canUseWechatVirtualPayment()) {
      reject(new Error('当前微信基础库不支持小程序虚拟支付，请升级微信或开发者工具后重试'))
      return
    }
    try {
      validateWechatVirtualPayParams(payParams)
    } catch (error) {
      reject(error)
      return
    }
    wx.requestVirtualPayment({
      ...payParams,
      success: resolve,
      fail(err) {
        reject(new Error(err?.errMsg || '小程序虚拟支付未完成'))
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
      scene: 'mini_program_virtual',
      appId: WECHAT_APPID,
      code,
      idempotencyKey: createIdempotencyKey(plan)
    })

    if (order.payParams?.mode !== 'wechat_virtual') {
      throw new Error(order.payParams?.message || '小程序虚拟支付参数未就绪')
    }
    await requestWechatVirtualPayment(order.payParams?.virtualPay || {})
    await confirmVirtualPaymentOrder(order.orderNo, {
      scene: 'mini_program_virtual',
      payResult: 'success'
    }).catch(() => null)
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

.feature-list {
  display: flex;
  flex-wrap: wrap;
  gap: 8rpx;
  margin-top: 14rpx;
}

.feature-list text {
  padding: 6rpx 12rpx;
  border-radius: 999rpx;
  background: #eef6ff;
  color: #1b5faa;
  font-size: 22rpx;
  font-weight: 700;
}

.pricing-note text {
  display: block;
  color: #2a3648;
  font-size: 25rpx;
  line-height: 1.6;
}

.pricing-note text:first-child {
  margin-bottom: 8rpx;
  color: #1a1a2e;
  font-size: 30rpx;
  font-weight: 900;
}
</style>
