<template>
  <view class="page">
    <text class="page-title">账号安全</text>
    <text class="page-desc">密码、协议状态和设备风险与后端安全接口同步。</text>

    <view class="card">
      <view class="section-head">
        <text class="section-title">修改密码</text>
      </view>
      <input v-model="passwordForm.oldPassword" class="field" password placeholder="当前密码" />
      <input v-model="passwordForm.newPassword" class="field field--mt" password placeholder="新密码" />
      <input v-model="passwordForm.confirmPassword" class="field field--mt" password placeholder="确认新密码" />
      <button class="primary-button form-button" :loading="passwordLoading" @tap="submitPassword">保存密码</button>
    </view>

    <view class="card">
      <view class="section-head">
        <text class="section-title">用户协议</text>
        <text class="muted">{{ termsStatus.hasAgreed ? '已同意' : '待确认' }}</text>
      </view>
      <view class="detail-row">
        <text>当前版本</text>
        <text>{{ termsStatus.latestVersion || '-' }}</text>
      </view>
      <view class="detail-row">
        <text>已同意版本</text>
        <text>{{ termsStatus.agreedVersion || '-' }}</text>
      </view>
      <view class="detail-row">
        <text>更新日期</text>
        <text>{{ termsStatus.updatedAt || '-' }}</text>
      </view>
      <button class="secondary-button form-button" @tap="goLegalDocuments">查看协议正文</button>
      <button
        v-if="termsStatus.needsUpdate"
        class="secondary-button form-button"
        :loading="termsLoading"
        @tap="agreeLatestTerms"
      >
        同意最新版
      </button>
    </view>

    <view class="card">
      <view class="section-head">
        <text class="section-title">设备风险</text>
        <text class="risk-tag" :class="`risk-tag--${deviceRisk.riskLevel || 'unknown'}`">
          {{ riskText }}
        </text>
      </view>
      <view class="detail-row">
        <text>设备数量</text>
        <text>{{ deviceRisk.deviceCount || 0 }}</text>
      </view>
      <view class="detail-row">
        <text>新设备</text>
        <text>{{ deviceRisk.isNewDevice ? '是' : '否' }}</text>
      </view>
      <text v-if="deviceRisk.warning" class="warning-text">{{ deviceRisk.warning }}</text>
      <button class="secondary-button form-button" :loading="deviceLoading" @tap="checkDevice">重新检测</button>
    </view>

    <view class="card">
      <view class="section-head">
        <text class="section-title">本地数据</text>
      </view>
      <text class="warning-text">清除收藏、训练进度、题库筛选、套餐本地缓存和设备标识，不会删除服务器账号数据。</text>
      <button class="secondary-button danger-button form-button" @tap="confirmClearLocalData">清除本地数据</button>
    </view>
  </view>
</template>

<script setup>
import { reactive, ref } from 'vue'
import { onShow } from '@dcloudio/uni-app'
import { agreeTerms, getDeviceRisk, getTermsStatus, updatePassword } from '../../api/user'
import {
  BILLING_STORAGE_KEY,
  PREFERENCES_STORAGE_KEY,
  PROVINCE_STORAGE_KEY,
  TRAINING_PROGRESS_STORAGE_KEY,
} from '../../utils/constants'
import { requireLogin, toast } from '../../utils/navigation'

const DEVICE_ID_KEY = 'civil_mini_device_id'
const SUPPORT_FEEDBACK_STORAGE_KEY = 'civil_support_feedback_records'
const passwordLoading = ref(false)
const termsLoading = ref(false)
const deviceLoading = ref(false)
const passwordForm = reactive({
  oldPassword: '',
  newPassword: '',
  confirmPassword: ''
})
const termsStatus = reactive({
  hasAgreed: false,
  agreedVersion: '',
  latestVersion: '',
  agreedAt: '',
  needsUpdate: false
})
const deviceRisk = reactive({
  riskLevel: 'unknown',
  isNewDevice: false,
  deviceCount: 0,
  warning: ''
})
const riskTextMap = {
  safe: '安全',
  low: '低风险',
  medium: '中风险',
  high: '高风险',
  unknown: '未知'
}
const riskText = ref('未知')

onShow(() => {
  if (!requireLogin()) return
  loadTerms()
  checkDevice()
})

function getDeviceId() {
  let deviceId = uni.getStorageSync(DEVICE_ID_KEY)
  if (!deviceId) {
    deviceId = `mp_${Date.now()}_${Math.random().toString(36).slice(2, 10)}`
    uni.setStorageSync(DEVICE_ID_KEY, deviceId)
  }
  return deviceId
}

function updateRiskText() {
  riskText.value = riskTextMap[deviceRisk.riskLevel] || '未知'
}

async function loadTerms() {
  termsLoading.value = true
  try {
    Object.assign(termsStatus, await getTermsStatus({ skipErrorHandler: true }))
  } catch (error) {
    toast(error?.message || '协议状态加载失败')
  } finally {
    termsLoading.value = false
  }
}

async function agreeLatestTerms() {
  if (!termsStatus.latestVersion) return
  termsLoading.value = true
  try {
    await agreeTerms(termsStatus.latestVersion)
    await loadTerms()
    toast('已同意最新版', 'success')
  } catch (error) {
    toast(error?.message || '协议确认失败')
  } finally {
    termsLoading.value = false
  }
}

async function checkDevice() {
  deviceLoading.value = true
  try {
    Object.assign(deviceRisk, await getDeviceRisk(getDeviceId(), { skipErrorHandler: true }))
    updateRiskText()
  } catch (error) {
    toast(error?.message || '设备检测失败')
  } finally {
    deviceLoading.value = false
  }
}

async function submitPassword() {
  if (!passwordForm.oldPassword || !passwordForm.newPassword) {
    toast('请填写完整密码')
    return
  }
  if (passwordForm.newPassword.length < 6) {
    toast('新密码至少 6 位')
    return
  }
  if (passwordForm.newPassword !== passwordForm.confirmPassword) {
    toast('两次新密码不一致')
    return
  }
  passwordLoading.value = true
  try {
    await updatePassword({
      oldPassword: passwordForm.oldPassword,
      newPassword: passwordForm.newPassword
    })
    passwordForm.oldPassword = ''
    passwordForm.newPassword = ''
    passwordForm.confirmPassword = ''
    toast('密码已更新', 'success')
  } catch (error) {
    toast(error?.message || '密码更新失败')
  } finally {
    passwordLoading.value = false
  }
}

function clearLocalData() {
  [
    BILLING_STORAGE_KEY,
    PREFERENCES_STORAGE_KEY,
    PROVINCE_STORAGE_KEY,
    TRAINING_PROGRESS_STORAGE_KEY,
    SUPPORT_FEEDBACK_STORAGE_KEY,
    DEVICE_ID_KEY
  ].forEach((key) => {
    try {
      uni.removeStorageSync(key)
    } catch {}
  })
  toast('本地缓存已清除', 'success')
}

function confirmClearLocalData() {
  uni.showModal({
    title: '确认清除本地数据？',
    content: '这不会删除服务器账号数据，但会清除本机缓存。为避免误退出登录，本次会保留登录态。',
    confirmText: '确认清除',
    confirmColor: '#cf1322',
    success(res) {
      if (res.confirm) clearLocalData()
    }
  })
}

function goLegalDocuments() {
  uni.navigateTo({ url: '/pages/legal/index' })
}
</script>

<style scoped>
.field--mt {
  margin-top: 16rpx;
}

.form-button {
  margin-top: 18rpx;
}

.detail-row {
  display: flex;
  justify-content: space-between;
  padding: 16rpx 0;
  border-bottom: 1rpx solid #eef2f6;
  color: #2a3648;
  font-size: 25rpx;
}

.detail-row:last-of-type {
  border-bottom: 0;
}

.detail-row text:last-child {
  color: #1a1a2e;
  font-weight: 700;
}

.risk-tag {
  color: #6f7c8f;
  font-size: 24rpx;
  font-weight: 800;
}

.risk-tag--safe {
  color: #389e0d;
}

.risk-tag--low,
.risk-tag--medium {
  color: #d48806;
}

.risk-tag--high {
  color: #cf1322;
}

.warning-text {
  display: block;
  margin-top: 12rpx;
  color: #cf1322;
  font-size: 24rpx;
  line-height: 1.6;
}
</style>
