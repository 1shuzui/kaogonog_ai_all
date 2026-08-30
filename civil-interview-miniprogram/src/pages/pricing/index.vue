<!--
小程序套餐中心只负责展示虚拟训练权益并发起微信官方小程序虚拟支付，不能出现普通微信支付或端侧模拟到账入口。
试用、套餐开通和权益叠加都依赖账号状态，所以未登录用户可看套餐，但支付前必须由用户主动触发登录。

@param: 无；页面读取套餐状态、用户登录态和支付环境配置。
@return: 渲染套餐卡片、当前权益摘要和虚拟支付发起按钮。
@raises: 不主动抛业务异常；接口失败、未登录和权限不足由请求层或页面提示承接。
-->
<template>
  <view class="page">
    <text class="page-title">套餐中心</text>

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
        <text class="plan-card__title">3小时套餐</text>
        <text class="plan-card__price">¥99</text>
        <text class="plan-card__desc">总计 3 小时训练时长，适合短期冲刺，按实际训练消耗。</text>
        <view class="feature-list">
          <text>完整全真模拟</text>
          <text>定向备面与专项训练</text>
          <text>可与已有权益叠加</text>
          <text>历史报告、收藏题和低分错题复盘</text>
        </view>
      </view>
      <button class="primary-button" :loading="loadingPlan === 'hourly'" :disabled="!!loadingPlan" @tap="activate('hourly')">开通</button>
    </view>

    <view class="plan-card card">
      <view>
        <text class="plan-card__title">包月套餐</text>
        <text class="plan-card__price">¥299</text>
        <text class="plan-card__desc">30 天有效期，每日 1 小时训练额度，适合稳定推进备考计划。</text>
        <view class="feature-list">
          <text>每日额度自动刷新</text>
          <text>完整付费训练模块</text>
          <text>续费和按时包可叠加汇总</text>
          <text>错题收藏、历史复盘和智能推荐</text>
        </view>
      </view>
      <button class="primary-button" :loading="loadingPlan === 'monthly'" :disabled="!!loadingPlan" @tap="activate('monthly')">开通</button>
    </view>

    <view class="card pricing-note">
      <text>支付说明</text>
      <text>付费权益允许叠加，系统会优先消耗更早到期的余额；支付成功后以账户权益同步结果为准。</text>
    </view>
  </view>
</template>

<script setup>
import { ref } from 'vue'
import {
  confirmVirtualPaymentOrder,
  createPaymentOrder,
  getPaymentOrder,
  verifyVirtualPaymentOrder
} from '../../api/payment'
import { useBillingStore } from '../../stores/billing'
import { useUserStore } from '../../stores/user'
import { promptLoginForAction, toast } from '../../utils/navigation'
import { getWechatLoginCode } from '../../utils/wechatLogin'

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
  const appBaseInfo = typeof wx.getAppBaseInfo === 'function' ? wx.getAppBaseInfo() : {}
  const sdkVersion = appBaseInfo.SDKVersion || ''
  return compareVersion(sdkVersion, '2.19.2') >= 0 || wx.canIUse?.('requestVirtualPayment') === true
}

function isIosDevice() {
  if (typeof wx === 'undefined') return false
  const deviceInfo = typeof wx.getDeviceInfo === 'function'
    ? wx.getDeviceInfo()
    : (typeof wx.getSystemInfoSync === 'function' ? wx.getSystemInfoSync() : {})
  const platform = String(deviceInfo.platform || deviceInfo.system || '').toLowerCase()
  return platform.includes('ios') || platform.includes('iphone') || platform.includes('ipad')
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
  if (isIosDevice() && Number(signData.env) === 1) {
    throw new Error('iOS 端小程序虚拟支付不支持沙箱环境，请切换现网虚拟支付配置后再开通')
  }
}

async function ensureLoginForVirtualPayment() {
  if (userStore.isAuthenticated) return true
  return promptLoginForAction('开通套餐', '/pages/pricing/index')
}

function loginForPayCode() {
  return getWechatLoginCode()
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
  for (let index = 0; index < 8; index += 1) {
    let order = await getPaymentOrder(orderNo)
    if (order?.status === 'paid') return order
    // wx.requestVirtualPayment 的 success 回调或首次确认请求都可能因退后台/网络抖动而丢失。
    // pending 时由后端重新向微信查单，端侧结果本身始终不能作为到账凭据。
    try {
      const verification = await verifyVirtualPaymentOrder(orderNo)
      order = verification?.order || order
      if (order?.status === 'paid') return order
    } catch {
      // 微信可能尚未把订单推进到“已支付待发货”，按原轮询节奏继续等待即可。
    }
    await new Promise((resolve) => setTimeout(resolve, 1500))
  }
  return null
}

async function activate(plan) {
  if (!PACKAGE_BY_PLAN[plan] || loadingPlan.value) return
  loadingPlan.value = plan
  try {
    if (!await ensureLoginForVirtualPayment()) return
    const code = await loginForPayCode()
    const order = await createPaymentOrder({
      packageCode: PACKAGE_BY_PLAN[plan],
      payChannel: 'wechat_virtual',
      scene: 'mini_program_virtual',
      appId: WECHAT_APPID,
      code,
      idempotencyKey: createIdempotencyKey(plan)
    })

    if (order.payParams?.mode !== 'wechat_virtual') {
      throw new Error(order.payParams?.message || '小程序虚拟支付参数未就绪')
    }
    const payResult = await requestWechatVirtualPayment(order.payParams?.virtualPay || {})
    try {
      await confirmVirtualPaymentOrder(order.orderNo, {
        scene: 'mini_program_virtual',
        payResult: 'success',
        outTradeNo: order.payParams?.virtualPayMeta?.outTradeNo || order.orderNo,
        rawResult: payResult || {}
      })
    } catch {
      toast('订单确认暂时失败，稍后将自动重试同步', 'warning')
    }
    const paidOrder = await waitOrderPaid(order.orderNo)
    await userStore.loadUserInfo()
    if (paidOrder) {
      toast('支付成功，权益已同步', 'success')
    } else {
      toast('支付已提交，权益同步中。如长时间未到账，请联系客服', 'warning')
    }
  } catch (error) {
    toast(error?.message || '支付未完成，请稍后重试')
  } finally {
    loadingPlan.value = ''
  }
}

function startTrial() {
  if (!promptLoginForAction('试用 1 题', '/pages/exam/prepare?trial=1')) return
  uni.navigateTo({ url: '/pages/exam/prepare?trial=1' })
}
</script>

<style scoped>
.pricing-status {
  border: 1rpx solid #DCEAF7;
  background: linear-gradient(135deg, #ffffff 0%, #EAF5FF 60%, #DFF0FF 100%);
  color: #172033;
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
  grid-template-columns: minmax(0, 1fr) 220rpx;
  gap: 20rpx;
  align-items: center;
}

.plan-card .primary-button {
  padding: 0 12rpx;
  font-size: 25rpx;
  line-height: 1.25;
  white-space: normal;
}

.plan-card__title {
  color: #172033;
  font-size: 32rpx;
  font-weight: 800;
}

.plan-card__price {
  margin-top: 8rpx;
  color: #2F7FD6;
  font-size: 38rpx;
  font-weight: 900;
}

.plan-card__desc {
  margin-top: 8rpx;
  color: #64748B;
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
  background: #EAF5FF;
  color: #2F7FD6;
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
  color: #172033;
  font-size: 30rpx;
  font-weight: 900;
}
</style>
