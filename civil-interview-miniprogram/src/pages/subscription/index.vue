<!--
这个小程序权益页展示当前套餐和剩余时长，练习入口的可用性也依赖这些数据。

@param: 无；页面运行时从 props、路由参数、Pinia 状态和用户点击中拿数据。
@return: 渲染当前业务界面，并把按钮、表单或跳转事件交给既有流程处理。
@raises: 不主动抛业务异常；接口失败、未登录和权限不足由请求层或页面提示承接。
-->
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
          <view class="entitlement-item__main">
            <text class="entitlement-item__title">{{ item.planName }}</text>
            <text class="entitlement-item__desc">
              剩余 {{ item.remainingMinutes }} 分钟，今日可用 {{ item.remainingDailyMinutes }} 分钟{{ item.expiresAt ? ` | 到期 ${formatDate(item.expiresAt)}` : '' }}
            </text>
          </view>
          <button
            class="entitlement-item__button"
            :class="{ 'entitlement-item__button--active': item.isActiveSelection }"
            size="mini"
            :loading="switchingId === item.subscriptionId"
            :disabled="item.isActiveSelection || !item.canUse || !!switchingId"
            @tap="switchEntitlement(item)"
          >
            {{ item.isActiveSelection ? '当前使用' : '切换使用' }}
          </button>
        </view>
      </view>
    </view>

    <view class="card">
      <view class="section-head">
        <text class="section-title">访问检查</text>
        <text class="muted">{{ access?.mode || 'practice' }}</text>
      </view>
      <view class="access-row">
        <button class="secondary-button" :loading="checkingMode === 'practice'" :disabled="!!checkingMode" @tap="checkAccess('practice')">专项练习</button>
        <button class="secondary-button" :loading="checkingMode === 'fullExam'" :disabled="!!checkingMode" @tap="checkAccess('fullExam')">全真模拟</button>
      </view>
      <text class="access-result" :class="{ 'access-result--ok': access?.allowed }">
        {{ accessText }}
      </text>
      <text v-if="lastCheckedAt" class="access-time">
        已于 {{ lastCheckedAt }} 完成访问检查
      </text>
    </view>

    <button class="primary-button" @tap="goPricing">开通或续费</button>
  </view>
</template>

<script setup>
import { computed, ref } from 'vue'
import { onShow } from '@dcloudio/uni-app'
import { useSubscriptionStore } from '../../stores/subscription'
import { formatDate } from '../../utils/format'
import { requireLogin, toast } from '../../utils/navigation'

const subscriptionStore = useSubscriptionStore()
const checkingMode = ref('')
const lastCheckedAt = ref('')
const switchingId = ref(0)
const status = computed(() => subscriptionStore.status)
const access = computed(() => subscriptionStore.access)
const planTitle = computed(() => status.value.planType === 'trial' ? '试用版' : '已开通套餐')
const statusDesc = computed(() => {
  if (!status.value.canUse) return '当前权益不可用'
  return status.value.stacked ? `当前可进入专项练习与全真模拟，已叠加 ${status.value.activePlanCount} 项权益` : '当前可进入专项练习与全真模拟'
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
  if (checkingMode.value) return
  checkingMode.value = mode
  try {
    const result = await subscriptionStore.check(mode, { skipErrorHandler: true })
    lastCheckedAt.value = formatCheckTime()
    if (!silent) {
      toast(result?.allowed ? '访问检查完成：允许进入' : `访问检查完成：${result?.reason || '暂不可用'}`, result?.allowed ? 'success' : 'none')
    }
  } catch (error) {
    if (!silent) toast(error?.message || '访问检查失败')
  } finally {
    checkingMode.value = ''
  }
}

async function switchEntitlement(item) {
  const subscriptionId = Number(item?.subscriptionId || item?.id || 0)
  if (!subscriptionId || item?.isActiveSelection || switchingId.value) return
  switchingId.value = subscriptionId
  try {
    await subscriptionStore.switchActive(subscriptionId, { skipErrorHandler: true })
    await checkAccess('practice', true)
    toast('已切换当前使用权益', 'success')
  } catch (error) {
    toast(error?.message || '切换权益失败')
  } finally {
    switchingId.value = 0
  }
}

function goPricing() {
  uni.navigateTo({ url: '/pages/pricing/index' })
}

function formatCheckTime() {
  const date = new Date()
  const pad = (value) => String(value).padStart(2, '0')
  return `${pad(date.getHours())}:${pad(date.getMinutes())}:${pad(date.getSeconds())}`
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
  border: 1rpx solid #DCEAF7;
  background: linear-gradient(135deg, #ffffff 0%, #EAF5FF 100%);
  color: #172033;
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
  color: #2F7FD6;
  font-size: 34rpx;
  font-weight: 900;
}

.metric__label {
  margin-top: 6rpx;
  color: #64748B;
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
  color: #172033;
  font-weight: 700;
}

.entitlement-list {
  display: grid;
  gap: 12rpx;
  margin-top: 18rpx;
}

.entitlement-item {
  display: grid;
  grid-template-columns: minmax(0, 1fr) 150rpx;
  gap: 14rpx;
  align-items: center;
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
  color: #172033;
  font-size: 25rpx;
  font-weight: 800;
}

.entitlement-item__desc {
  margin-top: 6rpx;
  color: #64748B;
  font-size: 22rpx;
}

.entitlement-item__button {
  width: 150rpx;
  min-height: 58rpx;
  padding: 0;
  border: 1rpx solid #2F7FD6;
  border-radius: 8rpx;
  background: #ffffff;
  color: #2F7FD6;
  font-size: 22rpx;
  line-height: 58rpx;
}

.entitlement-item__button--active {
  border-color: #389e0d;
  background: #f0f9eb;
  color: #389e0d;
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

.access-time {
  display: block;
  margin-top: 8rpx;
  color: #64748B;
  font-size: 22rpx;
}
</style>
