<!--
小程序登录页，承接用户主动点击后的微信快捷登录、账号补全、协议确认和“暂且跳过登录”。

审核要求进入首页不能强制授权，因此登录页只能在用户主动进入或被功能拦截后出现。
跳过登录会回到首页浏览，不请求手机号、头像或昵称；真正使用试用、练习、支付和个人数据时再要求登录。

@param: 无；登录状态来自 user store 和微信登录 API。
@return: 渲染登录按钮、协议勾选、跳过入口和错误提示。
@raises: 不主动抛业务异常；微信授权失败、接口失败或协议未确认由页面提示承接。
-->
<template>
  <view class="motion-page login-page" :class="motionClass" :style="motionStyle">
    <view class="login-card">
      <view class="login-brand">
        <text class="login-brand__title">公考面试AI测评</text>
        <text class="login-brand__subtitle">登录后保存练习记录，随时回来复盘。</text>
      </view>

      <view class="agreement-box">
        <checkbox class="agreement-box__checkbox" :checked="form.agreedTerms" aria-label="同意用户协议与隐私政策" @tap="toggleAgreement" />
        <view class="agreement-box__content">
          <text class="agreement-box__text">
            我已阅读并同意
            <text class="agreement-box__link" @tap.stop="goLegalDocuments">《用户协议》与《隐私政策》</text>
          </text>
          <text class="agreement-box__hint">请主动勾选后登录；先浏览无需勾选。</text>
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

      <text v-if="loginError" class="page-desc" role="alert">{{ loginError }}</text>
      <button class="primary-button wechat-login-button" :loading="wechatLoading" :disabled="loading || wechatLoading" @tap="loginByWechat">
        微信快捷登录
      </button>

      <button class="link-button browse-button" @tap="browseWithoutLogin">
        先浏览，暂不登录
      </button>

      <button class="link-button invite-toggle" :aria-expanded="inviteExpanded" @tap="inviteExpanded = !inviteExpanded">
        {{ form.inviteCode ? '已填写邀请码（选填）' : '有邀请码？选填' }} · {{ inviteExpanded ? '收起' : '展开' }}
      </button>
      <MotionCollapse :open="inviteExpanded">
        <view class="invite-fields">
          <view class="form-label">邀请码（选填）</view>
          <input v-model="form.inviteCode" class="field" aria-label="邀请码，选填" placeholder="请输入邀请码" />
          <text class="login-helper">没有邀请码也可以登录或注册。</text>
        </view>
      </MotionCollapse>

      <MotionCollapse class="password-login-section" title="已有 PC 账号？账号密码登录" :open="passwordLoginExpanded" :revision="mode" @toggle="passwordLoginExpanded = !passwordLoginExpanded">
        <view class="password-login-fields">
          <text class="login-helper">与电脑端共用账号。已有账号请直接登录，避免重复注册。</text>
          <view class="login-tabs">
            <button class="login-tabs__item" :class="{ 'login-tabs__item--active': mode === 'login' }" @tap="mode = 'login'">账号登录</button>
            <button class="login-tabs__item" :class="{ 'login-tabs__item--active': mode === 'register' }" @tap="mode = 'register'">注册账号</button>
          </view>
          <view class="form-label">用户名</view>
          <input v-model="form.username" class="field" aria-label="用户名" placeholder="请输入用户名" />
          <text v-if="mode === 'register'" class="login-helper">用户名为 3–32 位英文字母、数字、下划线或短横线，不能以 wxmp_ 开头。</text>

          <view class="form-label">密码</view>
          <view class="password-field">
            <input v-model="form.password" class="field password-field__input" :password="mode === 'login' ? !passwordVisibility.login : !passwordVisibility.register" aria-label="密码" placeholder="请输入密码" />
            <button
              class="password-field__toggle"
              :aria-label="`${mode === 'login' ? (passwordVisibility.login ? '隐藏' : '显示') : (passwordVisibility.register ? '隐藏' : '显示')}密码`"
              @tap="togglePasswordVisibility(mode === 'login' ? 'login' : 'register')"
            >
              <text class="password-field__eye" :class="{ 'password-field__eye--open': mode === 'login' ? passwordVisibility.login : passwordVisibility.register }"></text>
            </button>
          </view>
          <template v-if="mode === 'register'">
            <view class="form-label">确认密码</view>
            <view class="password-field">
              <input v-model="form.confirmPassword" class="field password-field__input" :password="!passwordVisibility.confirm" aria-label="确认密码" placeholder="请再次输入密码" />
              <button class="password-field__toggle" :aria-label="`${passwordVisibility.confirm ? '隐藏' : '显示'}确认密码`" @tap="togglePasswordVisibility('confirm')">
                <text class="password-field__eye" :class="{ 'password-field__eye--open': passwordVisibility.confirm }"></text>
              </button>
            </view>
          </template>
          <text v-if="loginError" class="login-helper" role="alert">{{ loginError }}</text>
          <button class="secondary-button login-submit" :loading="loading" :disabled="loading || wechatLoading" @tap="submit">{{ mode === 'login' ? '使用账号密码登录' : '注册账号' }}</button>
          <button v-if="mode === 'login'" class="link-button forgot-button" @tap="openResetPanel">忘记密码</button>
        </view>
      </MotionCollapse>
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
        <input v-model="accountSetupForm.username" class="field" maxlength="32" placeholder="设置新的登录用户名" />
        <text class="login-helper">3–32 位英文字母、数字、下划线或短横线，不能以 wxmp_ 开头。此处创建新登录名；已有 PC 账号请使用下方账号密码登录入口。</text>
        <text v-if="accountSetupError" class="login-helper" role="alert">{{ accountSetupError }}</text>
        <view class="form-label">PC 登录密码</view>
        <input v-model="accountSetupForm.password" class="field" password placeholder="至少 6 位" />
        <view class="form-label">确认密码</view>
        <input v-model="accountSetupForm.confirmPassword" class="field" password placeholder="请再次输入密码" />
        <button class="link-button invite-toggle" :aria-expanded="accountInviteExpanded" @tap="accountInviteExpanded = !accountInviteExpanded">
          邀请码（选填） · {{ accountInviteExpanded ? '收起' : '展开' }}
        </button>
        <MotionCollapse :open="accountInviteExpanded">
          <view class="form-label">邀请码（选填）</view>
          <input v-model="accountSetupForm.inviteCode" class="field" aria-label="账号补全邀请码，选填" placeholder="请输入邀请码" />
        </MotionCollapse>
        <button class="primary-button account-setup-panel__button" :loading="accountSetupLoading" @tap="submitAccountSetup">
          创建账号并进入
        </button>
        <button class="link-button" @tap="accountSetupVisible = false; mode = 'login'; passwordLoginExpanded = true">已有电脑账号？使用账号密码登录</button>
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
import MotionCollapse from '../../components/MotionCollapse.vue'
import { usePageMotion } from '../../motion/useMotion'
const { motionClass, motionStyle } = usePageMotion()
import { reactive, ref } from 'vue'
import { onLoad } from '@dcloudio/uni-app'
import { useUserStore } from '../../stores/user'
import { toast } from '../../utils/navigation'
import { getWechatLoginCode } from '../../utils/wechatLogin'

const userStore = useUserStore()
const mode = ref('login')
const passwordLoginExpanded = ref(false)
const loginError = ref('')
const accountSetupError = ref('')
const inviteExpanded = ref(false)
const accountInviteExpanded = ref(false)
const loading = ref(false)
const wechatLoading = ref(false)
const accountSetupVisible = ref(false)
const accountSetupLoading = ref(false)
const privacyAuthRequired = ref(false)
const privacyAuthorizationReady = ref(false)
const privacyContractName = ref('')
const redirectUrl = ref('')
const wechatInviteSessionToken = ref('')
const AGREED_TERMS_STORAGE_KEY = 'civil_agreed_terms_version'
const AGREED_TERMS_VERSION = '2026-05-12'
const form = reactive({
  username: '',
  password: '',
  confirmPassword: '',
  inviteCode: '',
  agreedTerms: false
})
const passwordVisibility = reactive({
  login: false,
  register: false,
  confirm: false
})
const accountSetupForm = reactive({
  username: '',
  password: '',
  confirmPassword: '',
  inviteCode: ''
})

function goHomeWithCachedSession() {
  goAfterLogin()
}

function clearLocalSession() {
  userStore.logout()
  toast('已清除本地登录态，请重新登录')
}

function togglePasswordVisibility(field) {
  if (Object.prototype.hasOwnProperty.call(passwordVisibility, field)) {
    passwordVisibility[field] = !passwordVisibility[field]
  }
}

function openResetPanel() {
  uni.navigateTo({ url: `/pages/login/reset?username=${encodeURIComponent(form.username.trim())}` })
}

onLoad((query = {}) => {
  form.username = query.username || ''
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
    if (!/^(?!wxmp_)[A-Za-z0-9_-]{3,32}$/i.test(form.username.trim())) {
      toast('用户名需为 3–32 位英文字母、数字、下划线或短横线，不能以 wxmp_ 开头')
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
    const inviteCode = form.inviteCode.trim()
    if (inviteCode && !/^[A-Za-z0-9_-]{3,32}$/.test(inviteCode)) {
      toast('邀请码需为 3-32 位字母、数字、_ 或 -')
      return false
    }
  }
  return true
}

function validateInviteCode(value) {
  const inviteCode = String(value || '').trim()
  if (inviteCode && !/^[A-Za-z0-9_-]{3,32}$/.test(inviteCode)) {
    toast('邀请码需为 3-32 位字母、数字、_ 或 -')
    return false
  }
  return true
}

async function submit() {
  if (loading.value || wechatLoading.value) return
  loginError.value = ''
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
      inviteCode: form.inviteCode.trim().toUpperCase(),
      agreedTermsVersion: '2026-05-12'
    })
    toast('注册成功，请登录', 'success')
    mode.value = 'login'
    form.password = ''
    form.confirmPassword = ''
    form.inviteCode = ''
    form.agreedTerms = false
  } catch (error) {
    loginError.value = error?.message || '操作失败，请重试'
  } finally {
    loading.value = false
  }
}

async function loginByWechat() {
  if (wechatLoading.value || loading.value) return
  loginError.value = ''
  if (!await ensurePrivacyReadyForLogin()) return
  if (!validateInviteCode(form.inviteCode)) return
  wechatLoading.value = true
  try {
    const code = await getWechatLoginCode()
    const result = await userStore.loginWithWechat(code, '2026-05-12', form.inviteCode.trim().toUpperCase())
    if (result?.requiresPcAccountSetup) {
      accountSetupVisible.value = true
      accountSetupError.value = ''
      wechatInviteSessionToken.value = result?.inviteSessionToken || ''
      accountSetupForm.username = result?.accountLogin?.pcLoginUsername || ''
      accountSetupForm.password = ''
      accountSetupForm.confirmPassword = ''
      accountSetupForm.inviteCode = ''
      toast('登录成功', 'success')
      return
    }
    toast('登录成功', 'success')
    goAfterLogin()
  } catch (error) {
    loginError.value = error?.message || '微信登录失败，请重试'
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
  if (username.toLowerCase().startsWith('wxmp_')) {
    toast('账号不能使用 wxmp_ 开头')
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
  const inviteCode = accountSetupForm.inviteCode.trim()
  if (inviteCode && !/^[A-Za-z0-9_-]{3,32}$/.test(inviteCode)) {
    toast('邀请码需为 3-32 位字母、数字、_ 或 -')
    return false
  }
  return true
}

async function submitAccountSetup() {
  if (accountSetupLoading.value) return
  if (!validateAccountSetup()) return
  accountSetupLoading.value = true
  accountSetupError.value = ''
  try {
    await userStore.setupWechatPcAccount({
      username: accountSetupForm.username.trim(),
      password: accountSetupForm.password,
      inviteCode: accountSetupForm.inviteCode.trim().toUpperCase(),
      inviteSessionToken: wechatInviteSessionToken.value
    })
    accountSetupVisible.value = false
    wechatInviteSessionToken.value = ''
    toast('PC 登录账号已创建', 'success')
    goAfterLogin()
  } catch (error) {
    accountSetupError.value = error?.message || '账号创建失败，请重试'
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
    async success(res) {
      if (res.confirm) {
        const inviteSessionToken = wechatInviteSessionToken.value
        const pendingInvite = accountSetupForm.inviteCode.trim().toUpperCase()
        if (pendingInvite && inviteSessionToken) {
          try {
            await userStore.bindWechatInvite({
              inviteCode: pendingInvite,
              inviteSessionToken
            })
          } catch (error) {
            toast(error?.message || '邀请码绑定失败')
            return
          }
        }
        accountSetupVisible.value = false
        wechatInviteSessionToken.value = ''
        goAfterLogin()
      }
    }
  })
}


function toggleAgreement() {
  form.agreedTerms = !form.agreedTerms
  if (form.agreedTerms) saveAcceptedTermsVersion()
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
  align-items: flex-start;
  justify-content: center;
  min-height: 100vh;
  padding: 24px 16px;
  padding-bottom: calc(24px + env(safe-area-inset-bottom));
  background: var(--ui-bg, #f7f9fd);
  color: var(--ui-text, #203047);
}

.login-card {
  width: 100%;
  max-width: 480px;
  padding: 24px 16px;
  border: 1px solid var(--ui-border, #dbe3ee);
  border-radius: 12px;
  background: #ffffff;
}

.login-brand {
  display: flex;
  align-items: flex-start;
  flex-direction: column;
  margin-bottom: 24px;
  text-align: left;
}

.login-brand__title {
  color: var(--ui-text, #203047);
  font-size: 24px;
  font-weight: 700;
  line-height: 1.4;
}

.login-brand__subtitle {
  margin-top: 8px;
  color: var(--ui-muted, #596a80);
  font-size: 14px;
  line-height: 1.6;
}

.login-tabs {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 8rpx;
  margin: 16px 0;
  padding: 4px;
  border-radius: 12px;
  background: var(--ui-bg, #f7f9fd);
}

.login-tabs__item {
  min-height: 44px;
  padding: 8px;
  border-radius: 8px;
  background: transparent;
  color: var(--ui-muted, #596a80);
  font-size: 14px;
  font-weight: 600;
  text-align: center;
}

.login-tabs__item--active {
  background: var(--ui-soft, #edf3ff);
  color: var(--ui-link, #285bc7);
}

.login-submit {
  margin-top: 24px;
}

.login-page .field {
  width: 100%;
  height: 44px;
  min-height: 44px;
  border-color: var(--ui-border, #dbe3ee);
  background: var(--ui-bg, #f7f9fd);
  color: var(--ui-text, #203047);
  font-size: 16px;
}

.login-page .form-label { margin-top: 16px; color: var(--ui-text, #203047); font-size: 14px; }
.login-page .field::placeholder { color: var(--ui-muted, #596a80); }
.login-page button { min-height: 44px; font-size: 14px; }
.login-page .primary-button { background: var(--ui-primary, #326be5); border-color: var(--ui-primary, #326be5); color: #ffffff; box-shadow: none; }
.login-page .secondary-button { background: #ffffff; border-color: var(--ui-border, #dbe3ee); color: var(--ui-link, #285bc7); box-shadow: none; }
.login-page .danger-button { color: #a94b2b; }
.login-page button:focus-visible, .login-page input:focus-visible { outline: 2px solid var(--ui-link, #285bc7); outline-offset: 2px; }

.login-helper { display: block; margin-top: 8px; color: var(--ui-muted, #596a80); font-size: 14px; line-height: 1.6; }
.password-login-section { border-top: 1px solid var(--ui-border, #dbe3ee); }
.password-login-fields { padding-bottom: 8px; }
.invite-fields { padding-bottom: 16px; }

.password-field {
  display: flex;
  align-items: center;
  gap: 12rpx;
}

.password-field__input {
  flex: 1;
  min-width: 0;
}

.password-field__toggle {
  flex: 0 0 44px;
  min-height: 44px;
  padding: 0;
  border: 1px solid var(--ui-border, #dbe3ee);
  border-radius: 14rpx;
  background: var(--ui-bg, #f7f9fd);
  color: var(--ui-link, #285bc7);
}

.password-field__eye {
  position: relative;
  display: inline-block;
  width: 34rpx;
  height: 22rpx;
  border: 3rpx solid currentColor;
  border-radius: 70% 0;
  transform: rotate(45deg);
}

.password-field__eye::after {
  position: absolute;
  top: 50%;
  left: 50%;
  width: 8rpx;
  height: 8rpx;
  border-radius: 50%;
  background: currentColor;
  content: '';
  transform: translate(-50%, -50%) rotate(-45deg);
}

.password-field__eye:not(.password-field__eye--open)::before {
  position: absolute;
  top: 50%;
  left: -5rpx;
  width: 44rpx;
  height: 3rpx;
  background: currentColor;
  content: '';
  transform: translateY(-50%) rotate(-45deg);
}

.forgot-button {
  margin-top: 14rpx;
}

.wechat-login-button {
  margin-top: 16px;
}

.login-page .wechat-login-button { font-size: 16px; }

.browse-button {
  margin-top: 8px;
  color: var(--ui-link, #285bc7);
  font-size: 14px;
}

.agreement-box {
  display: flex;
  align-items: flex-start;
  gap: 8px;
  margin-top: 16px;
}

.agreement-box__checkbox { display: flex; align-items: center; justify-content: center; flex: 0 0 44px; min-height: 44px; }

.agreement-box__content {
  flex: 1;
  min-width: 0;
}

.agreement-box__text,
.agreement-tip {
  display: block;
  color: var(--ui-muted, #596a80);
  font-size: 14px;
  line-height: 1.7;
}

.agreement-box__hint {
  display: block;
  margin-top: 4rpx;
  color: var(--ui-muted, #596a80);
  font-size: 14px;
  line-height: 1.55;
}

.agreement-box__link {
  display: inline-block;
  min-height: 44px;
  padding: 8px 0;
  color: var(--ui-link, #285bc7);
}

.privacy-auth-panel {
  margin-top: 16rpx;
  padding: 18rpx;
  border: 1px solid var(--ui-border, #dbe3ee);
  border-radius: 14rpx;
  background: var(--ui-soft, #edf3ff);
}

.privacy-auth-panel__text {
  display: block;
  color: var(--ui-muted, #596a80);
  font-size: 14px;
  line-height: 1.6;
}

.privacy-auth-panel__button {
  margin-top: 14rpx;
  min-height: 44px;
  font-size: 14px;
}

.link-button {
  min-height: 44px;
  padding: 8px;
  background: transparent;
  color: var(--ui-link, #285bc7);
  font-size: 14px;
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
  min-height: 44px;
  font-size: 14px;
}

.account-setup-mask {
  position: fixed;
  top: 0;
  right: 0;
  bottom: 0;
  left: 0;
  z-index: 20;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 32rpx;
  background: rgba(18, 32, 50, 0.42);
}

.account-setup-panel {
  width: 100%;
  max-width: 480px;
  max-height: calc(100vh - 64px);
  overflow-y: auto;
  padding: 36rpx 30rpx;
  border-radius: 20rpx;
  background: #ffffff;
  box-shadow: 0 28rpx 70rpx rgba(20, 40, 70, 0.24);
}

.account-setup-panel__title {
  display: block;
  color: var(--ui-text, #203047);
  font-size: 20px;
  font-weight: 700;
}

.account-setup-panel__desc,
.account-setup-panel__tip {
  display: block;
  margin-top: 14rpx;
  color: var(--ui-muted, #596a80);
  font-size: 14px;
  line-height: 1.65;
}

.account-setup-panel__button {
  margin-top: 26rpx;
}

.account-setup-panel__skip {
  margin-top: 12rpx;
}
</style>
