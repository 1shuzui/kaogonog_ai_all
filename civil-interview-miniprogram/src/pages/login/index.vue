<!--
小程序登录页，承接用户主动点击后的微信快捷登录、账号补全、协议确认和“暂且跳过登录”。

审核要求进入首页不能强制授权，因此登录页只能在用户主动进入或被功能拦截后出现。
跳过登录会回到首页浏览，不请求手机号、头像或昵称；真正使用试用、练习、支付和个人数据时再要求登录。

@param: 无；登录状态来自 user store 和微信登录 API。
@return: 渲染登录按钮、协议勾选、跳过入口和错误提示。
@raises: 不主动抛业务异常；微信授权失败、接口失败或协议未确认由页面提示承接。
-->
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
      </template>

      <view class="agreement-box">
        <checkbox :checked="form.agreedTerms" @tap="toggleAgreement" />
        <view class="agreement-box__content">
          <text class="agreement-box__text">
            我已阅读并同意
            <text class="agreement-box__link" @tap.stop="goLegalDocuments">《用户协议》与《隐私政策》</text>
          </text>
          <text class="agreement-box__hint">未勾选前无法登录、注册或发起微信快捷登录。</text>
        </view>
      </view>

      <view v-if="privacyAuthRequired" class="privacy-auth-panel">
        <text class="privacy-auth-panel__text">
          微信要求先确认{{ privacyContractName || '小程序隐私保护指引' }}，请阅读后点击下方按钮。
        </text>
        <button
          class="secondary-button privacy-auth-panel__button"
          open-type="agreePrivacyAuthorization"
          @agreeprivacyauthorization="onAgreePrivacyAuthorization"
        >
          我已阅读并确认微信隐私授权
        </button>
      </view>

      <button class="primary-button login-submit" :loading="loading" @tap="submit">
        {{ mode === 'login' ? '登录' : '注册' }}
      </button>

      <button v-if="mode === 'login'" class="secondary-button wechat-login-button" :loading="wechatLoading" @tap="loginByWechat">
        微信快捷登录
      </button>

      <button class="link-button browse-button" @tap="browseWithoutLogin">
        暂且跳过登录，先浏览功能
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

    <view v-if="accountSetupVisible" class="account-setup-mask">
      <view class="account-setup-panel">
        <text class="account-setup-panel__title">创建 PC 登录账号</text>
        <text class="account-setup-panel__desc">
          微信快捷登录已完成。请设置一个自己记得住的账号和密码，之后 PC 端用这个账号密码登录，就能同步小程序里的练习记录、收藏错题和订单权益。
        </text>
        <view class="form-label">PC 登录账号</view>
        <input v-model="accountSetupForm.username" class="field" placeholder="3-32 位字母/数字/下划线" />
        <view class="form-label">PC 登录密码</view>
        <input v-model="accountSetupForm.password" class="field" password placeholder="至少 6 位" />
        <view class="form-label">确认密码</view>
        <input v-model="accountSetupForm.confirmPassword" class="field" password placeholder="请再次输入密码" />
        <button class="primary-button account-setup-panel__button" :loading="accountSetupLoading" @tap="submitAccountSetup">
          创建账号并进入
        </button>
        <button class="link-button account-setup-panel__skip" @tap="skipAccountSetup">
          暂时跳过
        </button>
        <text class="account-setup-panel__tip">
          跳过后仍可继续使用小程序微信登录；但 PC 端暂时不能用账号密码进入同一账号，可稍后在“我的-账号安全”补设。
        </text>
      </view>
    </view>
  </view>
</template>

<script setup>
import { reactive, ref } from 'vue'
import { onLoad } from '@dcloudio/uni-app'
import {
  confirmPasswordReset,
  requestPasswordReset,
  verifyPasswordReset
} from '../../api/auth'
import { useUserStore } from '../../stores/user'
import { toast } from '../../utils/navigation'
import { getWechatLoginCode } from '../../utils/wechatLogin'

const userStore = useUserStore()
const mode = ref('login')
const loading = ref(false)
const wechatLoading = ref(false)
const accountSetupVisible = ref(false)
const accountSetupLoading = ref(false)
const resetVisible = ref(false)
const resetLoading = ref(false)
const resetRequesting = ref(false)
const resetTip = ref('')
const privacyAuthRequired = ref(false)
const privacyAuthorizationReady = ref(false)
const privacyContractName = ref('')
const redirectUrl = ref('')
const AGREED_TERMS_STORAGE_KEY = 'civil_agreed_terms_version'
const AGREED_TERMS_VERSION = '2026-05-12'
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
const accountSetupForm = reactive({
  username: '',
  password: '',
  confirmPassword: ''
})

function goHomeWithCachedSession() {
  goAfterLogin()
}

function clearLocalSession() {
  userStore.logout()
  toast('已清除本地登录态，请重新登录')
}

function openResetPanel() {
  resetVisible.value = true
  resetForm.username = form.username.trim()
}

onLoad((query = {}) => {
  redirectUrl.value = decodeURIComponent(query.redirect || '')
  restoreAgreementState()
})

function goAfterLogin() {
  const url = redirectUrl.value || '/pages/home/index'
  if (url.startsWith('/pages/home/index') || url.startsWith('/pages/targeted/index') || url.startsWith('/pages/bank/index') || url.startsWith('/pages/training/index') || url.startsWith('/pages/profile/index')) {
    uni.switchTab({ url: url.split('?')[0] })
    return
  }
  uni.redirectTo({ url })
}

function browseWithoutLogin() {
  uni.switchTab({ url: '/pages/home/index' })
}

function readAcceptedTermsVersion() {
  try {
    return uni.getStorageSync(AGREED_TERMS_STORAGE_KEY) || ''
  } catch {
    return ''
  }
}

function saveAcceptedTermsVersion() {
  try {
    uni.setStorageSync(AGREED_TERMS_STORAGE_KEY, AGREED_TERMS_VERSION)
  } catch {
    // ignore storage failures
  }
}

function restoreAgreementState() {
  form.agreedTerms = readAcceptedTermsVersion() === AGREED_TERMS_VERSION
}

function loadWechatPrivacySetting() {
  return new Promise((resolve) => {
    if (typeof wx === 'undefined' || typeof wx.getPrivacySetting !== 'function') {
      privacyAuthRequired.value = false
      privacyAuthorizationReady.value = true
      resolve()
      return
    }
    wx.getPrivacySetting({
      success(res) {
        privacyAuthRequired.value = !!res.needAuthorization
        privacyContractName.value = res.privacyContractName || '小程序隐私保护指引'
        if (!res.needAuthorization) {
          privacyAuthorizationReady.value = true
        }
        resolve()
      },
      fail() {
        privacyAuthRequired.value = false
        privacyAuthorizationReady.value = true
        resolve()
      }
    })
  })
}

function validateTermsAgreement() {
  if (!form.agreedTerms) {
    toast('请先阅读并勾选同意用户协议与隐私政策')
    return false
  }
  if (privacyAuthRequired.value && !privacyAuthorizationReady.value) {
    toast('请先阅读并确认微信隐私授权')
    return false
  }
  return true
}

async function ensurePrivacyReadyForLogin() {
  await loadWechatPrivacySetting()
  return validateTermsAgreement()
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
  if (!validateTermsAgreement()) {
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
  }
  return true
}

async function submit() {
  if (loading.value) return
  if (!validate()) return
  if (!await ensurePrivacyReadyForLogin()) return
  loading.value = true
  try {
    if (mode.value === 'login') {
      await userStore.login(form.username.trim(), form.password)
      toast('登录成功', 'success')
      goAfterLogin()
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

async function loginByWechat() {
  if (wechatLoading.value) return
  if (!await ensurePrivacyReadyForLogin()) return
  wechatLoading.value = true
  try {
    const code = await getWechatLoginCode()
    const result = await userStore.loginWithWechat(code, '2026-05-12')
    if (result?.requiresPcAccountSetup) {
      accountSetupVisible.value = false
      toast('登录成功', 'success')
      goAfterLogin()
      return
    }
    toast('登录成功', 'success')
    goAfterLogin()
  } catch (error) {
    toast(error?.message || '微信登录失败')
  } finally {
    wechatLoading.value = false
  }
}

function validateAccountSetup() {
  const username = accountSetupForm.username.trim()
  if (!/^[A-Za-z0-9_-]{3,32}$/.test(username)) {
    toast('账号需为 3-32 位字母、数字、下划线或短横线')
    return false
  }
  if (username.startsWith('wx_')) {
    toast('账号不能使用 wx_ 开头')
    return false
  }
  if (accountSetupForm.password.length < 6) {
    toast('密码至少 6 位')
    return false
  }
  if (accountSetupForm.password !== accountSetupForm.confirmPassword) {
    toast('两次密码输入不一致')
    return false
  }
  return true
}

async function submitAccountSetup() {
  if (accountSetupLoading.value) return
  if (!validateAccountSetup()) return
  accountSetupLoading.value = true
  try {
    await userStore.setupWechatPcAccount({
      username: accountSetupForm.username.trim(),
      password: accountSetupForm.password
    })
    accountSetupVisible.value = false
    toast('PC 登录账号已创建', 'success')
    goAfterLogin()
  } catch (error) {
    toast(error?.message || '账号创建失败')
  } finally {
    accountSetupLoading.value = false
  }
}

function skipAccountSetup() {
  uni.showModal({
    title: '暂时跳过？',
    content: '跳过后可以继续用微信进入小程序，但 PC 端暂时不能用账号密码登录同一账号。之后可在“我的-账号安全”补设。',
    confirmText: '先跳过',
    cancelText: '继续设置',
    success(res) {
      if (res.confirm) {
        accountSetupVisible.value = false
        goAfterLogin()
      }
    }
  })
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
  if (form.agreedTerms) {
    saveAcceptedTermsVersion()
  }
}

function onAgreePrivacyAuthorization() {
  privacyAuthorizationReady.value = true
  toast(form.agreedTerms ? '已确认微信隐私授权，可继续登录' : '已确认微信隐私授权，请手动勾选用户协议与隐私政策', 'success')
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
  background: linear-gradient(180deg, #EAF5FF 0%, #F6FAFE 42%, #F6FAFE 100%);
}

.login-card {
  width: 100%;
  padding: 52rpx 34rpx 36rpx;
  border-radius: 20rpx;
  background: #ffffff;
  box-shadow: 0 24rpx 60rpx rgba(47, 127, 214, 0.10);
}

.login-brand {
  display: flex;
  align-items: center;
  flex-direction: column;
  margin-bottom: 36rpx;
  text-align: center;
}

.login-brand__title {
  color: #2F7FD6;
  font-size: 42rpx;
  font-weight: 800;
}

.login-brand__subtitle {
  margin-top: 10rpx;
  color: #64748B;
  font-size: 25rpx;
}

.login-tabs {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 8rpx;
  margin-bottom: 24rpx;
  padding: 8rpx;
  border-radius: 14rpx;
  background: #F6FAFE;
}

.login-tabs__item {
  padding: 18rpx 0;
  border-radius: 10rpx;
  color: #64748B;
  font-size: 28rpx;
  font-weight: 600;
  text-align: center;
}

.login-tabs__item--active {
  background: #ffffff;
  color: #2F7FD6;
  box-shadow: 0 4rpx 12rpx rgba(47, 127, 214, 0.07);
}

.login-submit {
  margin-top: 34rpx;
}

.forgot-button {
  margin-top: 14rpx;
}

.wechat-login-button {
  margin-top: 18rpx;
}

.browse-button {
  margin-top: 18rpx;
  color: #2F7FD6;
  font-size: 27rpx;
}

.agreement-box {
  display: flex;
  align-items: flex-start;
  gap: 12rpx;
  margin-top: 18rpx;
}

.agreement-box__content {
  flex: 1;
  min-width: 0;
}

.agreement-box__text,
.agreement-tip {
  display: block;
  color: #64748B;
  font-size: 24rpx;
  line-height: 1.7;
}

.agreement-box__hint {
  display: block;
  margin-top: 4rpx;
  color: #9aa6b5;
  font-size: 22rpx;
  line-height: 1.55;
}

.agreement-box__link {
  color: #2F7FD6;
}

.privacy-auth-panel {
  margin-top: 16rpx;
  padding: 18rpx;
  border: 1rpx solid #d9e8f7;
  border-radius: 14rpx;
  background: #f4f9fe;
}

.privacy-auth-panel__text {
  display: block;
  color: #526579;
  font-size: 23rpx;
  line-height: 1.6;
}

.privacy-auth-panel__button {
  margin-top: 14rpx;
  min-height: 72rpx;
  font-size: 24rpx;
}

.link-button {
  min-height: 64rpx;
  background: transparent;
  color: #2F7FD6;
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
  color: #2F7FD6;
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

.account-setup-mask {
  position: fixed;
  inset: 0;
  z-index: 20;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 32rpx;
  background: rgba(18, 32, 50, 0.42);
}

.account-setup-panel {
  width: 100%;
  padding: 36rpx 30rpx;
  border-radius: 20rpx;
  background: #ffffff;
  box-shadow: 0 28rpx 70rpx rgba(20, 40, 70, 0.24);
}

.account-setup-panel__title {
  display: block;
  color: #172033;
  font-size: 34rpx;
  font-weight: 800;
}

.account-setup-panel__desc,
.account-setup-panel__tip {
  display: block;
  margin-top: 14rpx;
  color: #5f6f84;
  font-size: 24rpx;
  line-height: 1.65;
}

.account-setup-panel__button {
  margin-top: 26rpx;
}

.account-setup-panel__skip {
  margin-top: 12rpx;
}
</style>
