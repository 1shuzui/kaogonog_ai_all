<template>
  <view class="login-page">
    <view class="login-card">
      <view class="login-brand">
        <text class="login-brand__title">公考面试AI测评</text>
        <text class="login-brand__subtitle">智能评分 / 精准诊断 / 高效提分</text>
      </view>

      <view class="login-tabs">
        <view
          class="login-tabs__item"
          :class="{ 'login-tabs__item--active': mode === 'login' }"
          @tap="mode = 'login'"
        >
          登录
        </view>
        <view
          class="login-tabs__item"
          :class="{ 'login-tabs__item--active': mode === 'register' }"
          @tap="mode = 'register'"
        >
          注册
        </view>
      </view>

      <view class="form-label">用户名</view>
      <input v-model="form.username" class="field" placeholder="请输入用户名" />

      <view class="form-label">密码</view>
      <input v-model="form.password" class="field" password placeholder="请输入密码" />

      <template v-if="mode === 'register'">
        <view class="form-label">确认密码</view>
        <input v-model="form.confirmPassword" class="field" password placeholder="请再次输入密码" />
        <view class="agreement-box">
          <checkbox :checked="form.agreedTerms" @tap="toggleAgreement" />
          <text class="agreement-box__text">
            我已阅读并同意
            <text class="agreement-box__link" @tap.stop="goLegalDocuments">《用户协议》与《隐私协议》</text>
          </text>
        </view>
      </template>

      <view v-else class="agreement-tip">
        登录即表示您已阅读并同意
        <text class="agreement-box__link" @tap="goLegalDocuments">《用户协议》与《隐私协议》</text>
      </view>

      <button class="primary-button login-submit" :loading="loading" @tap="submit">
        {{ mode === 'login' ? '登录' : '注册' }}
      </button>

      <button v-if="mode === 'login'" class="link-button forgot-button" @tap="openResetPanel">
        忘记密码
      </button>

      <view v-if="resetVisible" class="reset-panel">
        <view class="section-head">
          <text class="section-title">找回密码</text>
          <text class="muted" @tap="resetVisible = false">收起</text>
        </view>
        <view class="form-label">用户名</view>
        <input v-model="resetForm.username" class="field" placeholder="请输入要找回的用户名" />
        <view class="form-label">邮箱或手机号（可选）</view>
        <input v-model="resetForm.contact" class="field" placeholder="若已绑定邮箱，可填写用于校验" />
        <view class="reset-code-row">
          <input v-model="resetForm.code" class="field reset-code-row__input" placeholder="验证码" />
          <button class="secondary-button reset-code-row__button" :loading="resetRequesting" @tap="requestResetCode">
            获取验证码
          </button>
        </view>
        <text v-if="resetTip" class="reset-tip">{{ resetTip }}</text>
        <view class="form-label">新密码</view>
        <input v-model="resetForm.newPassword" class="field" password placeholder="至少 6 位" />
        <view class="form-label">确认新密码</view>
        <input v-model="resetForm.confirmPassword" class="field" password placeholder="请再次输入新密码" />
        <button class="primary-button reset-submit" :loading="resetLoading" @tap="confirmResetPassword">
          重置密码
        </button>
      </view>

      <view v-if="userStore.isAuthenticated" class="session-tools">
        <button class="secondary-button session-tools__button" @tap="goHomeWithCachedSession">进入已登录首页</button>
        <button class="secondary-button danger-button session-tools__button" @tap="clearLocalSession">清除本地登录态</button>
      </view>
    </view>
  </view>
</template>

<script setup>
import { reactive, ref } from 'vue'
import {
  confirmPasswordReset,
  requestPasswordReset,
  verifyPasswordReset
} from '../../api/auth'
import { useUserStore } from '../../stores/user'
import { toast } from '../../utils/navigation'

const userStore = useUserStore()
const mode = ref('login')
const loading = ref(false)
const resetVisible = ref(false)
const resetLoading = ref(false)
const resetRequesting = ref(false)
const resetTip = ref('')
const form = reactive({
  username: '',
  password: '',
  confirmPassword: '',
  agreedTerms: false
})
const resetForm = reactive({
  username: '',
  contact: '',
  code: '',
  newPassword: '',
  confirmPassword: ''
})

function goHomeWithCachedSession() {
  uni.switchTab({ url: '/pages/home/index' })
}

function clearLocalSession() {
  userStore.logout()
  toast('已清除本地登录态，请重新登录')
}

function openResetPanel() {
  resetVisible.value = true
  resetForm.username = form.username.trim()
}

function validate() {
  if (!form.username.trim()) {
    toast('请输入用户名')
    return false
  }
  if (!form.password) {
    toast('请输入密码')
    return false
  }
  if (mode.value === 'register') {
    if (form.username.trim().length < 3) {
      toast('用户名至少 3 个字符')
      return false
    }
    if (form.password.length < 6) {
      toast('密码至少 6 个字符')
      return false
    }
    if (form.password !== form.confirmPassword) {
      toast('两次密码输入不一致')
      return false
    }
    if (!form.agreedTerms) {
      toast('请先阅读并同意用户协议与隐私协议')
      return false
    }
  }
  return true
}

async function submit() {
  if (loading.value) return
  if (!validate()) return
  loading.value = true
  try {
    if (mode.value === 'login') {
      await userStore.login(form.username.trim(), form.password)
      toast('登录成功', 'success')
      uni.switchTab({ url: '/pages/home/index' })
      return
    }

    await userStore.register({
      username: form.username.trim(),
      password: form.password,
      agreedTermsVersion: '2026-05-12'
    })
    toast('注册成功，请登录', 'success')
    mode.value = 'login'
    form.password = ''
    form.confirmPassword = ''
    form.agreedTerms = false
  } catch (error) {
    toast(error?.message || '操作失败')
  } finally {
    loading.value = false
  }
}

async function requestResetCode() {
  const username = resetForm.username.trim()
  if (!username) {
    toast('请先填写用户名')
    return
  }
  resetRequesting.value = true
  resetTip.value = ''
  try {
    const result = await requestPasswordReset({
      username,
      contact: resetForm.contact.trim()
    })
    resetTip.value = result?.debugCode
      ? `验证码：${result.debugCode}。短信未接入时请由管理员转交。`
      : (result?.message || '验证码已生成，请查收。')
    toast('验证码已生成', 'success')
  } catch (error) {
    toast(error?.message || '验证码生成失败')
  } finally {
    resetRequesting.value = false
  }
}

async function confirmResetPassword() {
  const username = resetForm.username.trim()
  const code = resetForm.code.trim()
  if (!username || !code) {
    toast('请填写用户名和验证码')
    return
  }
  if (resetForm.newPassword.length < 6) {
    toast('新密码至少 6 位')
    return
  }
  if (resetForm.newPassword !== resetForm.confirmPassword) {
    toast('两次新密码不一致')
    return
  }
  resetLoading.value = true
  try {
    await verifyPasswordReset({ username, code })
    await confirmPasswordReset({
      username,
      code,
      newPassword: resetForm.newPassword
    })
    form.username = username
    form.password = ''
    resetForm.code = ''
    resetForm.newPassword = ''
    resetForm.confirmPassword = ''
    resetTip.value = ''
    resetVisible.value = false
    toast('密码已重置，请登录', 'success')
  } catch (error) {
    toast(error?.message || '密码重置失败')
  } finally {
    resetLoading.value = false
  }
}

function toggleAgreement() {
  form.agreedTerms = !form.agreedTerms
}

function goLegalDocuments() {
  uni.navigateTo({ url: '/pages/legal/index' })
}
</script>

<style scoped>
.login-page {
  display: flex;
  align-items: center;
  justify-content: center;
  min-height: 100vh;
  padding: 44rpx 30rpx;
  background: linear-gradient(180deg, #e8f4fd 0%, #f0f5fa 42%, #f0f5fa 100%);
}

.login-card {
  width: 100%;
  padding: 52rpx 34rpx 36rpx;
  border-radius: 20rpx;
  background: #ffffff;
  box-shadow: 0 24rpx 60rpx rgba(21, 71, 122, 0.14);
}

.login-brand {
  display: flex;
  align-items: center;
  flex-direction: column;
  margin-bottom: 36rpx;
  text-align: center;
}

.login-brand__title {
  color: #1b5faa;
  font-size: 42rpx;
  font-weight: 800;
}

.login-brand__subtitle {
  margin-top: 10rpx;
  color: #6f7c8f;
  font-size: 25rpx;
}

.login-tabs {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 8rpx;
  margin-bottom: 24rpx;
  padding: 8rpx;
  border-radius: 14rpx;
  background: #f0f5fa;
}

.login-tabs__item {
  padding: 18rpx 0;
  border-radius: 10rpx;
  color: #6f7c8f;
  font-size: 28rpx;
  font-weight: 600;
  text-align: center;
}

.login-tabs__item--active {
  background: #ffffff;
  color: #1b5faa;
  box-shadow: 0 4rpx 12rpx rgba(23, 48, 78, 0.08);
}

.login-submit {
  margin-top: 34rpx;
}

.forgot-button {
  margin-top: 14rpx;
}

.agreement-box {
  display: flex;
  align-items: flex-start;
  gap: 12rpx;
  margin-top: 18rpx;
}

.agreement-box__text,
.agreement-tip {
  color: #6f7c8f;
  font-size: 24rpx;
  line-height: 1.7;
}

.agreement-box__link {
  color: #1b5faa;
}

.link-button {
  min-height: 64rpx;
  background: transparent;
  color: #1b5faa;
  font-size: 25rpx;
}

.reset-panel {
  margin-top: 24rpx;
  padding-top: 24rpx;
  border-top: 1rpx solid #eef2f6;
}

.reset-code-row {
  display: grid;
  grid-template-columns: minmax(0, 1fr) 170rpx;
  gap: 12rpx;
  margin-top: 16rpx;
}

.reset-code-row__input {
  margin-top: 0;
}

.reset-code-row__button {
  min-height: 86rpx;
  font-size: 24rpx;
}

.reset-tip {
  display: block;
  margin-top: 12rpx;
  color: #1b5faa;
  font-size: 23rpx;
  line-height: 1.5;
}

.reset-submit {
  margin-top: 24rpx;
}

.session-tools {
  display: grid;
  grid-template-columns: 1fr;
  gap: 14rpx;
  margin-top: 24rpx;
}

.session-tools__button {
  min-height: 76rpx;
  font-size: 25rpx;
}
</style>
