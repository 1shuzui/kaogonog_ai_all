<template>
  <view class="page page--tab">
    <view class="profile-card">
      <view class="profile-card__avatar">{{ initial }}</view>
      <view class="profile-card__copy">
        <text class="profile-card__name">{{ userStore.displayName }}</text>
        <text class="profile-card__meta">{{ userStore.selectedProvinceName }} · {{ billingStore.plan.title }}</text>
      </view>
    </view>

    <StatGrid :items="statItems" />

    <view class="card">
      <view class="section-head">
        <text class="section-title">练习偏好</text>
      </view>
      <picker :range="provinceNames" :value="provinceIndex" @change="onProvinceChange">
        <view class="setting-row">
          <text>默认省份</text>
          <text>{{ userStore.selectedProvinceName }}</text>
        </view>
      </picker>
      <view class="setting-slider">
        <text>准备时间 {{ preferences.defaultPrepTime }} 秒</text>
        <slider :value="preferences.defaultPrepTime" min="30" max="300" step="10" activeColor="#1b5faa" @change="onPrepChange" />
      </view>
      <view class="setting-slider">
        <text>作答时间 {{ preferences.defaultAnswerTime }} 秒</text>
        <slider :value="preferences.defaultAnswerTime" min="60" max="600" step="10" activeColor="#1b5faa" @change="onAnswerChange" />
      </view>
      <button class="primary-button" @tap="savePreferences">保存设置</button>
    </view>

    <view class="menu-list">
      <view class="menu-item card" @tap="goHistory">
        <text>历史记录</text>
        <text class="menu-item__arrow">›</text>
      </view>
      <view class="menu-item card" @tap="goPricing">
        <text>套餐中心</text>
        <text class="menu-item__arrow">›</text>
      </view>
    </view>

    <view class="card">
      <view class="section-head">
        <text class="section-title">关于</text>
      </view>
      <text class="about-text">公考面试AI智能测评系统小程序端 v1.0.0</text>
      <text class="about-text about-text--muted">与网页端并行，复用现有业务后端接口。</text>
    </view>

    <button class="secondary-button danger-button" @tap="logout">退出登录</button>
  </view>
</template>

<script setup>
import { computed, reactive } from 'vue'
import { onShow } from '@dcloudio/uni-app'
import StatGrid from '../../components/StatGrid.vue'
import { useBillingStore } from '../../stores/billing'
import { useHistoryStore } from '../../stores/history'
import { useUserStore } from '../../stores/user'
import { PROVINCES } from '../../utils/constants'
import { requireLogin, toast } from '../../utils/navigation'

const userStore = useUserStore()
const historyStore = useHistoryStore()
const billingStore = useBillingStore()
const preferences = reactive({
  defaultPrepTime: 90,
  defaultAnswerTime: 180,
  enableAudio: true
})

const initial = computed(() => userStore.displayName.slice(0, 1).toUpperCase())
const provinceOptions = computed(() => userStore.provinces.length ? userStore.provinces : PROVINCES)
const provinceNames = computed(() => provinceOptions.value.map((item) => item.name))
const provinceIndex = computed(() => Math.max(0, provinceOptions.value.findIndex((item) => item.code === userStore.selectedProvince)))
const statItems = computed(() => [
  { label: '练习次数', value: historyStore.stats?.totalExams || 0 },
  { label: '最高分', value: historyStore.bestScore || 0 },
  { label: '当前套餐', value: billingStore.plan.title }
])

onShow(async () => {
  if (!requireLogin()) return
  await Promise.allSettled([
    userStore.loadProvinces(),
    userStore.loadUserInfo(),
    historyStore.fetchStats()
  ])
  Object.assign(preferences, userStore.preferences)
})

function onProvinceChange(event) {
  const selected = provinceOptions.value[Number(event.detail.value)]
  userStore.setProvince(selected?.code || 'national')
}

function onPrepChange(event) {
  preferences.defaultPrepTime = Number(event.detail.value)
}

function onAnswerChange(event) {
  preferences.defaultAnswerTime = Number(event.detail.value)
}

async function savePreferences() {
  await userStore.savePreferences({ ...preferences })
  toast('设置已保存', 'success')
}

function goHistory() {
  uni.navigateTo({ url: '/pages/history/index' })
}

function goPricing() {
  uni.navigateTo({ url: '/pages/pricing/index' })
}

function logout() {
  userStore.logout()
  uni.reLaunch({ url: '/pages/login/index' })
}
</script>

<style scoped>
.profile-card {
  display: flex;
  align-items: center;
  margin-bottom: 20rpx;
  padding: 30rpx;
  border-radius: 18rpx;
  background: #ffffff;
  box-shadow: 0 6rpx 18rpx rgba(23, 48, 78, 0.06);
}

.profile-card__avatar {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 108rpx;
  height: 108rpx;
  margin-right: 24rpx;
  border-radius: 999rpx;
  background: linear-gradient(135deg, #1b5faa 0%, #5fa0e8 100%);
  color: #ffffff;
  font-size: 42rpx;
  font-weight: 800;
}

.profile-card__name {
  display: block;
  color: #1a1a2e;
  font-size: 36rpx;
  font-weight: 800;
}

.profile-card__meta {
  display: block;
  margin-top: 8rpx;
  color: #6f7c8f;
  font-size: 24rpx;
}

.setting-row {
  display: flex;
  justify-content: space-between;
  padding: 20rpx 0;
  border-bottom: 1rpx solid #eef2f6;
  color: #2a3648;
  font-size: 27rpx;
}

.setting-row text:last-child {
  color: #1b5faa;
  font-weight: 600;
}

.setting-slider {
  padding: 22rpx 0;
  color: #2a3648;
  font-size: 26rpx;
}

.menu-item {
  display: flex;
  align-items: center;
  justify-content: space-between;
  color: #1f2b3d;
  font-size: 29rpx;
}

.menu-item__arrow {
  color: #8c8c8c;
  font-size: 44rpx;
  line-height: 1;
}

.about-text {
  display: block;
  color: #2a3648;
  font-size: 26rpx;
  line-height: 1.7;
}

.about-text--muted {
  color: #6f7c8f;
  font-size: 23rpx;
}
</style>
