<template>
  <view class="page page--tab">
    <view class="profile-card">
      <view class="profile-card__avatar">{{ initial }}</view>
      <view class="profile-card__copy">
        <text class="profile-card__name">{{ safeDisplayName }}</text>
        <text class="profile-card__meta">{{ userStore.selectedProvinceName }} · {{ safePlanTitle }}</text>
        <text v-if="userStore.isAdmin" class="profile-card__badge">管理员权限</text>
      </view>
    </view>

    <view class="profile-stats">
      <view v-for="item in statItems" :key="item.label" class="profile-stats__item">
        <text class="profile-stats__value">{{ item.value }}</text>
        <text class="profile-stats__label">{{ item.label }}</text>
      </view>
    </view>

    <view v-if="profileLoading" class="sync-strip">正在同步账户信息...</view>
    <view v-else-if="profileError" class="sync-strip sync-strip--error" @tap="refreshProfile">
      {{ profileError }}，点此重试
    </view>

    <view class="card balance-card">
      <view>
        <text class="balance-card__label">当前权益余额</text>
        <text class="balance-card__title">{{ balanceTitle }}</text>
        <text class="balance-card__desc">{{ balanceDescription }}</text>
      </view>
      <button class="secondary-button balance-card__button" @tap="goSubscription">查看权益</button>
    </view>

    <view class="card">
      <view class="section-head">
        <text class="section-title">考试设置</text>
      </view>
      <picker :range="provinceNames" :value="provinceIndex" @change="onProvinceChange">
        <view class="setting-row">
          <text>默认省份</text>
          <text>{{ userStore.selectedProvinceName }}</text>
        </view>
      </picker>
      <picker :range="examCatPrefNames" :value="examCatPrefIndex" @change="onExamCatPrefChange">
        <view class="setting-row">
          <text>考试大类</text>
          <text>{{ selectedExamCatPrefName }}</text>
        </view>
      </picker>
      <view class="setting-block">
        <view class="setting-block__head">
          <text>注重题型</text>
          <text>{{ preferredQuestionLabel }}</text>
        </view>
        <view class="preference-chip-grid">
          <view
            v-for="item in preferredQuestionOptions"
            :key="item.key"
            class="preference-chip"
            :class="{ 'preference-chip--active': isPreferredQuestionSelected(item.key) }"
            @tap="togglePreferredQuestion(item.key)"
          >
            <text>{{ item.name }}</text>
          </view>
        </view>
        <text class="setting-hint">可留空，留空时系统按随机题型练习。</text>
      </view>
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
      <view class="menu-item card" @tap="goFavorites">
        <text>错题本 / 收藏夹</text>
        <text class="menu-item__arrow">›</text>
      </view>
      <view class="menu-item card" @tap="goPricing">
        <text>套餐中心</text>
        <text class="menu-item__arrow">›</text>
      </view>
      <view class="menu-item card" @tap="goSubscription">
        <text>订阅权益</text>
        <text class="menu-item__arrow">›</text>
      </view>
      <view class="menu-item card" @tap="goOrders">
        <text>订单记录</text>
        <text class="menu-item__arrow">›</text>
      </view>
      <view class="menu-item card" @tap="goSecurity">
        <text>账号安全</text>
        <text class="menu-item__arrow">›</text>
      </view>
      <view class="menu-item card" @tap="contactSupport">
        <text>客服反馈中心</text>
        <text class="menu-item__arrow">›</text>
      </view>
      <view class="menu-item card" @tap="goLegalDocuments">
        <text>用户协议与隐私协议</text>
        <text class="menu-item__arrow">›</text>
      </view>
      <view v-if="userStore.isAdmin" class="menu-item card" @tap="goAdmin">
        <text>管理员中心</text>
        <text class="menu-item__arrow">›</text>
      </view>
    </view>

    <view class="card">
      <view class="section-head">
        <text class="section-title">关于</text>
      </view>
      <text class="about-text">公考面试AI智能测评系统小程序端 v1.0.0</text>
    </view>

    <button class="secondary-button danger-button" @tap="logout">退出登录</button>
  </view>
</template>

<script setup>
import { computed, reactive, ref } from 'vue'
import { onShow } from '@dcloudio/uni-app'
import { useBillingStore } from '../../stores/billing'
import { useFavoritesStore } from '../../stores/favorites'
import { useHistoryStore } from '../../stores/history'
import { useUserStore } from '../../stores/user'
import { PROVINCES, QUESTION_CATEGORIES } from '../../utils/constants'
import { DEFAULT_TARGETED_POSITION_TREE } from '../../utils/targetedOptions'
import { logger } from '../../utils/logger'
import { requireLogin, toast } from '../../utils/navigation'

const userStore = useUserStore()
const historyStore = useHistoryStore()
const billingStore = useBillingStore()
const favoritesStore = useFavoritesStore()
const preferences = reactive({
  defaultPrepTime: 90,
  defaultAnswerTime: 180,
  enableAudio: true,
  preferredQuestionDimensions: [],
  practicePreferenceConfirmed: false,
  examCategory: ''
})
const profileLoading = ref(false)
const profileError = ref('')
let profileLoadTask = null

const safeDisplayName = computed(() => String(userStore.displayName || userStore.username || '考生'))
const initial = computed(() => safeDisplayName.value.slice(0, 1).toUpperCase() || '我')
const provinceOptions = computed(() => userStore.provinces.length ? userStore.provinces : PROVINCES)
const provinceNames = computed(() => provinceOptions.value.map((item) => item.name))
const provinceIndex = computed(() => Math.max(0, provinceOptions.value.findIndex((item) => item.code === userStore.selectedProvince)))
// Exam category preference
const examCatPrefOpts = DEFAULT_TARGETED_POSITION_TREE
const examCatPrefNames = computed(() => ['不限', ...examCatPrefOpts.map(c => c.name)])
const examCatPrefIndex = computed(() => {
  const name = preferences.examCategory
  if (!name) return 0
  const idx = examCatPrefOpts.findIndex(c => c.name === name)
  return idx >= 0 ? idx + 1 : 0
})
const selectedExamCatPrefName = computed(() => {
  if (!preferences.examCategory) return '不限'
  return preferences.examCategory
})
function onExamCatPrefChange(e) {
  const idx = Number(e.detail.value)
  preferences.examCategory = idx === 0 ? '' : (examCatPrefOpts[idx - 1]?.name || '')
}
const preferredQuestionOptions = QUESTION_CATEGORIES.filter((item) => item.key)
const preferredQuestionLabel = computed(() => {
  if (!preferences.preferredQuestionDimensions.length) return '随机'
  const names = preferences.preferredQuestionDimensions
    .map((key) => preferredQuestionOptions.find((item) => item.key === key)?.name)
    .filter(Boolean)
  return names.join('、') || '随机'
})
const safePlanTitle = computed(() => {
  if (userStore.isAdmin) return '管理员完整权限'
  return billingStore.plan?.title || '试用版'
})
const balanceTitle = computed(() => {
  if (userStore.isAdmin) return '管理员完整权限'
  return safePlanTitle.value
})
const balanceDescription = computed(() => {
  if (userStore.isAdmin) return '管理员账号不扣减套餐余额，可访问全部训练与管理功能。'
  const daily = Number(billingStore.remainingDailyMinutes || 0)
  const total = Number(billingStore.remainingMinutes || 0)
  if (total > 0 || daily > 0) {
    return `剩余总时长 ${total} 分钟，今日可用 ${daily || total} 分钟。`
  }
  return billingStore.plan?.status || '开通套餐后可查看剩余额度。'
})
const statItems = computed(() => [
  { label: '练习次数', value: historyStore.stats?.totalExams || 0 },
  { label: '最高分', value: historyStore.bestScore || 0 },
  { label: '错题收藏', value: favoritesStore.count }
])

onShow(() => {
  if (!requireLogin()) return
  refreshProfile()
})

function withTimeout(promise, timeoutMs, label) {
  let timer = null
  const timeout = new Promise((_, reject) => {
    timer = setTimeout(() => reject(new Error(`${label} 请求超时`)), timeoutMs)
  })
  return Promise.race([promise, timeout]).then((value) => {
    if (timer) clearTimeout(timer)
    return value
  }, (error) => {
    if (timer) clearTimeout(timer)
    throw error
  })
}

function settleAll(promises) {
  if (typeof Promise.allSettled === 'function') {
    return Promise.allSettled(promises)
  }
  return Promise.all(promises.map((promise) => Promise.resolve(promise)
    .then((value) => ({ status: 'fulfilled', value }))
    .catch((reason) => ({ status: 'rejected', reason }))))
}

function getErrorMessage(error, fallback = '同步失败') {
  return String(error?.message || error?.errMsg || error || fallback)
}

function normalizePagePreferences(raw = {}) {
  const validDimensions = new Set(preferredQuestionOptions.map((item) => item.key))
  const preferredQuestionDimensions = Array.isArray(raw.preferredQuestionDimensions)
    ? raw.preferredQuestionDimensions
      .map((item) => String(item || '').trim())
      .filter((item, index, list) => validDimensions.has(item) && list.indexOf(item) === index)
    : []
  return {
    defaultPrepTime: Math.max(30, Number(raw.defaultPrepTime || preferences.defaultPrepTime || 90)),
    defaultAnswerTime: Math.max(60, Number(raw.defaultAnswerTime || preferences.defaultAnswerTime || 180)),
    enableAudio: raw.enableAudio !== false && raw.enableVideo !== false,
    preferredQuestionDimensions,
    practicePreferenceConfirmed: raw.practicePreferenceConfirmed === true,
    examCategory: raw.examCategory || preferences.examCategory || ''
  }
}

function applyPreferencesFromStore() {
  Object.assign(preferences, normalizePagePreferences(userStore.preferences))
}

async function refreshProfile() {
  if (profileLoadTask) return profileLoadTask
  profileLoading.value = true
  profileError.value = ''
  const task = (async () => {
    const results = await settleAll([
      withTimeout(userStore.loadProvinces(), 8000, '省份配置'),
      withTimeout(userStore.loadUserInfo(), 10000, '账户信息'),
      withTimeout(historyStore.fetchStats(), 6000, '练习统计')
    ])
    applyPreferencesFromStore()
    const [provinceResult, accountResult, statsResult] = results
    if (provinceResult?.status === 'rejected') {
      logger.warn('Profile province sync failed', {
        event: 'mini.profile.province_sync_failed',
        error: provinceResult.reason
      })
    }
    if (statsResult?.status === 'rejected') {
      logger.warn('Profile stats sync failed', {
        event: 'mini.profile.stats_sync_failed',
        error: statsResult.reason
      })
    }
    if (accountResult?.status === 'rejected') {
      logger.error('Profile account sync failed', {
        event: 'mini.profile.account_sync_failed',
        error: accountResult.reason
      })
      if (!userStore.userInfo?.id && !userStore.username) {
        profileError.value = `账户信息同步失败：${getErrorMessage(accountResult.reason)}`
      }
    }
    return results
  })()

  profileLoadTask = task.then((result) => {
    profileLoading.value = false
    profileLoadTask = null
    return result
  }, (error) => {
    profileLoading.value = false
    profileLoadTask = null
    if (!userStore.userInfo?.id && !userStore.username) {
      profileError.value = `账户信息同步失败：${getErrorMessage(error)}`
    }
    return null
  })
  return profileLoadTask
}

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

function isPreferredQuestionSelected(key) {
  return preferences.preferredQuestionDimensions.includes(key)
}

function togglePreferredQuestion(key) {
  if (!key) return
  if (isPreferredQuestionSelected(key)) {
    preferences.preferredQuestionDimensions = preferences.preferredQuestionDimensions.filter((item) => item !== key)
    return
  }
  preferences.preferredQuestionDimensions = [...preferences.preferredQuestionDimensions, key]
}

async function savePreferences() {
  await userStore.savePreferences({
    ...preferences,
    practicePreferenceConfirmed: true
  })
  toast('设置已保存', 'success')
}

function goHistory() {
  uni.navigateTo({ url: '/pages/history/index' })
}

function goFavorites() {
  uni.navigateTo({ url: '/pages/favorites/index' })
}

function goPricing() {
  uni.navigateTo({ url: '/pages/pricing/index' })
}

function goSubscription() {
  uni.navigateTo({ url: '/pages/subscription/index' })
}

function goOrders() {
  uni.navigateTo({ url: '/pages/billing/orders' })
}

function goSecurity() {
  uni.navigateTo({ url: '/pages/account/security' })
}

function contactSupport() {
  uni.navigateTo({ url: '/pages/support/index' })
}

function goLegalDocuments() {
  uni.navigateTo({ url: '/pages/legal/index' })
}

function goAdmin() {
  uni.navigateTo({ url: '/pages/admin/index' })
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
  overflow: hidden;
  color: #1a1a2e;
  font-size: 36rpx;
  font-weight: 800;
  line-height: 1.25;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.profile-card__meta {
  display: block;
  margin-top: 8rpx;
  color: #6f7c8f;
  font-size: 24rpx;
}

.profile-card__copy {
  flex: 1;
  min-width: 0;
}

.profile-card__badge {
  display: inline-flex;
  margin-top: 12rpx;
  padding: 6rpx 14rpx;
  border-radius: 999rpx;
  background: #e8f4fd;
  color: #1b5faa;
  font-size: 22rpx;
  font-weight: 700;
}

.profile-stats {
  display: flex;
  gap: 16rpx;
  margin-bottom: 20rpx;
}

.profile-stats__item {
  flex: 1;
  min-width: 0;
  min-height: 120rpx;
  padding: 22rpx 12rpx;
  border: 1rpx solid rgba(27, 95, 170, 0.08);
  border-radius: 16rpx;
  background: #ffffff;
  text-align: center;
  box-shadow: 0 6rpx 18rpx rgba(23, 48, 78, 0.05);
}

.profile-stats__value {
  display: block;
  overflow: hidden;
  color: #1b5faa;
  font-size: 32rpx;
  font-weight: 800;
  line-height: 1.2;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.profile-stats__label {
  display: block;
  margin-top: 8rpx;
  color: #6f7c8f;
  font-size: 23rpx;
}

.sync-strip {
  margin-bottom: 20rpx;
  padding: 16rpx 22rpx;
  border: 1rpx solid #d9e3ef;
  border-radius: 14rpx;
  background: #f8fbff;
  color: #6f7c8f;
  font-size: 24rpx;
}

.sync-strip--error {
  border-color: #ffd6d6;
  background: #fff5f5;
  color: #cf1322;
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

.setting-block {
  padding: 22rpx 0;
  border-bottom: 1rpx solid #eef2f6;
}

.setting-block__head {
  display: flex;
  justify-content: space-between;
  gap: 16rpx;
  color: #2a3648;
  font-size: 27rpx;
}

.setting-block__head text:last-child {
  overflow: hidden;
  max-width: 430rpx;
  color: #1b5faa;
  font-weight: 700;
  text-align: right;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.preference-chip-grid {
  display: flex;
  flex-wrap: wrap;
  gap: 12rpx;
  margin-top: 18rpx;
}

.preference-chip {
  padding: 12rpx 18rpx;
  border: 1rpx solid #d9e3ef;
  border-radius: 999rpx;
  background: #ffffff;
  color: #2a3648;
  font-size: 24rpx;
  font-weight: 700;
}

.preference-chip--active {
  border-color: #1b5faa;
  background: #e8f4fd;
  color: #1b5faa;
}

.setting-hint {
  display: block;
  margin-top: 14rpx;
  color: #8a96a8;
  font-size: 22rpx;
  line-height: 1.5;
}

.balance-card {
  display: flex;
  gap: 18rpx;
  align-items: center;
  justify-content: space-between;
}

.balance-card__label,
.balance-card__title,
.balance-card__desc {
  display: block;
}

.balance-card__label {
  color: #1b5faa;
  font-size: 23rpx;
  font-weight: 800;
}

.balance-card__title {
  margin-top: 6rpx;
  color: #1a1a2e;
  font-size: 32rpx;
  font-weight: 900;
}

.balance-card__desc {
  margin-top: 6rpx;
  color: #6f7c8f;
  font-size: 24rpx;
  line-height: 1.5;
}

.balance-card__button {
  flex: 0 0 180rpx;
  min-height: 76rpx;
  font-size: 25rpx;
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
