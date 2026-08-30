<!--
PC 登录页，承接账号密码登录和注册入口；管理员与普通用户共用认证链路，路由守卫只在登录后分流。

登录页只负责收集凭证和跳转意图，不在页面内判断管理员权限或写权益状态；这些都以后端用户信息和路由守卫为准。

@param: 无；重定向目标来自路由 query，登录结果写入 user store。
@return: 渲染登录/注册表单，并在认证成功后回到目标页面或首页。
@raises: 不主动抛业务异常；账号密码错误、接口失败或协议问题由页面提示承接。
-->
<template>
  <div class="login-page">
    <div class="login-card">
      <div class="login-header">
        <h1>公考面试AI智能测评</h1>
        <p>智能评分 / 精准诊断 / 高效提分</p>
      </div>

      <a-tabs v-model:activeKey="activeTab" centered>
        <a-tab-pane key="login" tab="登录">
          <a-form
            :model="loginForm"
            :rules="loginRules"
            ref="loginFormRef"
            layout="vertical"
            @finish="handleLogin"
          >
            <a-form-item name="username" label="用户名">
              <a-input
                v-model:value="loginForm.username"
                placeholder="请输入用户名"
                size="large"
                :prefix="h(UserOutlined)"
              />
            </a-form-item>
            <a-form-item name="password" label="密码">
              <a-input-password
                v-model:value="loginForm.password"
                placeholder="请输入密码"
                size="large"
                :prefix="h(LockOutlined)"
              />
            </a-form-item>
            <div class="login-tools">
              <a-button type="link" size="small" @click="resetVisible = true">忘记密码</a-button>
            </div>
            <a-form-item name="agreedTerms">
              <a-checkbox :checked="loginForm.agreedTerms" @change="handleAgreementChange">
                我已阅读并同意
                <a-button type="link" size="small" @click.stop="$router.push('/legal')">《用户协议》与《隐私协议》</a-button>
              </a-checkbox>
            </a-form-item>
            <a-form-item>
              <a-button
                type="primary"
                html-type="submit"
                size="large"
                block
                :loading="loading"
              >
                登录
              </a-button>
            </a-form-item>
          </a-form>
        </a-tab-pane>

        <a-tab-pane key="register" tab="注册">
          <a-form
            :model="registerForm"
            :rules="registerRules"
            ref="registerFormRef"
            layout="vertical"
            @finish="handleRegister"
          >
            <a-form-item name="username" label="用户名">
              <a-input
                v-model:value="registerForm.username"
                placeholder="请输入用户名"
                size="large"
                :prefix="h(UserOutlined)"
              />
            </a-form-item>
            <a-form-item name="password" label="密码">
              <a-input-password
                v-model:value="registerForm.password"
                placeholder="请输入密码"
                size="large"
                :prefix="h(LockOutlined)"
              />
            </a-form-item>
            <a-form-item name="confirmPassword" label="确认密码">
              <a-input-password
                v-model:value="registerForm.confirmPassword"
                placeholder="请再次输入密码"
                size="large"
                :prefix="h(LockOutlined)"
              />
            </a-form-item>
            <a-form-item name="inviteCode" label="邀请码（选填）">
              <a-input
                v-model:value="registerForm.inviteCode"
                placeholder="请输入邀请码"
                size="large"
                :prefix="h(TagOutlined)"
              />
            </a-form-item>
            <a-form-item name="agreedTerms">
              <a-checkbox :checked="registerForm.agreedTerms" @change="handleAgreementChange">
                我已阅读并同意
                <a-button type="link" size="small" @click.stop="$router.push('/legal')">《用户协议》与《隐私协议》</a-button>
              </a-checkbox>
            </a-form-item>
            <a-form-item>
              <a-button
                type="primary"
                html-type="submit"
                size="large"
                block
                :loading="loading"
              >
                注册
              </a-button>
            </a-form-item>
          </a-form>
        </a-tab-pane>
      </a-tabs>

    </div>

    <a-modal
      v-model:open="resetVisible"
      title="找回密码"
      :footer="null"
      :destroy-on-close="false"
      width="460px"
    >
      <a-alert
        type="info"
        show-icon
        message="管理员核验后发送验证码"
        description="先提交用户名和可联系的邮箱或手机号。收到管理员发送的验证码后，可直接在下方设置新密码。"
      />
      <a-form class="reset-form" layout="vertical">
        <a-form-item label="用户名" required>
          <a-input v-model:value="resetForm.username" placeholder="请输入要找回的用户名" />
        </a-form-item>
        <a-form-item label="管理员核验联系方式（选填）">
          <a-input v-model:value="resetForm.contact" placeholder="可联系的邮箱或手机号" />
        </a-form-item>
        <a-button block :loading="resetRequesting" @click="handleResetRequest">
          提交验证码申请
        </a-button>
        <a-alert v-if="resetTip" class="reset-form__tip" type="success" show-icon :message="resetTip" />
        <a-divider />
        <a-form-item label="管理员发送的验证码" required>
          <a-input v-model:value="resetForm.code" maxlength="6" placeholder="6 位验证码" />
        </a-form-item>
        <a-form-item label="新密码" required>
          <a-input-password v-model:value="resetForm.newPassword" placeholder="至少 6 位" />
        </a-form-item>
        <a-form-item label="确认新密码" required>
          <a-input-password v-model:value="resetForm.confirmPassword" placeholder="再次输入新密码" />
        </a-form-item>
        <a-button type="primary" block :loading="resetConfirming" @click="handleResetConfirm">
          重置密码
        </a-button>
      </a-form>
    </a-modal>
  </div>
</template>

<script setup>
import { ref, reactive, h } from 'vue'
import { useRoute } from 'vue-router'
import { message } from 'ant-design-vue'
import { LockOutlined, TagOutlined, UserOutlined } from '@ant-design/icons-vue'
import {
  confirmPasswordReset,
  requestPasswordReset,
  verifyPasswordReset
} from '@/api/auth'
import { useUserStore } from '@/stores/user'

const route = useRoute()
const userStore = useUserStore()

const activeTab = ref('login')
const loading = ref(false)
const loginFormRef = ref(null)
const registerFormRef = ref(null)
const resetVisible = ref(false)
const resetRequesting = ref(false)
const resetConfirming = ref(false)
const resetTip = ref('')
const AGREED_TERMS_STORAGE_KEY = 'civil_agreed_terms_version'
const AGREED_TERMS_VERSION = '2026-05-12'

const loginForm = reactive({ username: '', password: '', agreedTerms: false })
const registerForm = reactive({ username: '', password: '', confirmPassword: '', inviteCode: '', agreedTerms: false })
const resetForm = reactive({ username: '', contact: '', code: '', newPassword: '', confirmPassword: '' })

const loginRules = {
  username: [{ required: true, message: '请输入用户名', trigger: 'blur' }],
  password: [{ required: true, message: '请输入密码', trigger: 'blur' }],
  agreedTerms: [
    {
      validator: (_, value) => {
        if (!value) {
          return Promise.reject('请先阅读并同意用户协议与隐私协议')
        }
        return Promise.resolve()
      },
      trigger: 'change'
    }
  ]
}

const registerRules = {
  username: [
    { required: true, message: '请输入用户名', trigger: 'blur' },
    { min: 3, message: '用户名至少3个字符', trigger: 'blur' }
  ],
  password: [
    { required: true, message: '请输入密码', trigger: 'blur' },
    { min: 6, message: '密码至少6个字符', trigger: 'blur' }
  ],
  confirmPassword: [
    { required: true, message: '请确认密码', trigger: 'blur' },
    {
      validator: (_, value) => {
        if (value !== registerForm.password) {
          return Promise.reject('两次密码输入不一致')
        }
        return Promise.resolve()
      },
      trigger: 'blur'
    }
  ],
  inviteCode: [
    {
      validator: (_, value) => {
        const code = String(value || '').trim()
        if (!code || /^[A-Za-z0-9_-]{3,32}$/.test(code)) {
          return Promise.resolve()
        }
        return Promise.reject('邀请码需为 3-32 位字母、数字、_ 或 -')
      },
      trigger: 'blur'
    }
  ],
  agreedTerms: [
    {
      validator: (_, value) => {
        if (!value) {
          return Promise.reject('请先阅读并同意用户协议与隐私协议')
        }
        return Promise.resolve()
      },
      trigger: 'change'
    }
  ]
}

function readAcceptedTermsVersion() {
  try {
    return localStorage.getItem(AGREED_TERMS_STORAGE_KEY) || ''
  } catch {
    return ''
  }
}

function saveAcceptedTermsVersion() {
  try {
    localStorage.setItem(AGREED_TERMS_STORAGE_KEY, AGREED_TERMS_VERSION)
  } catch {
    // ignore storage failures
  }
}

function restoreAgreementState() {
  const accepted = readAcceptedTermsVersion() === AGREED_TERMS_VERSION
  loginForm.agreedTerms = accepted
  registerForm.agreedTerms = accepted
}

function handleAgreementChange(event) {
  const checked = typeof event === 'boolean'
    ? event
    : !!event?.target?.checked
  loginForm.agreedTerms = checked
  registerForm.agreedTerms = checked
  if (checked) {
    saveAcceptedTermsVersion()
  }
}

restoreAgreementState()

function normalizeRedirectTarget(value) {
  const raw = Array.isArray(value) ? value[0] : value
  if (typeof raw !== 'string' || !raw.startsWith('/') || raw.startsWith('//')) {
    return '/'
  }
  return raw || '/'
}

async function handleLogin() {
  loading.value = true
  try {
    await userStore.login(loginForm.username, loginForm.password)
    message.success('登录成功')
    const redirect = normalizeRedirectTarget(route.query.redirect)
    window.location.replace(redirect)
  } catch (e) {
    const msg = e.normalizedMessage || e.response?.data?.detail || '登录失败'
    message.error(msg)
  } finally {
    loading.value = false
  }
}

async function handleRegister() {
  loading.value = true
  try {
    await userStore.register({
      username: registerForm.username,
      password: registerForm.password,
      inviteCode: registerForm.inviteCode.trim().toUpperCase(),
      agreedTermsVersion: '2026-05-12'
    })
    message.success('注册成功，请登录')
    activeTab.value = 'login'
    loginForm.username = registerForm.username
    loginForm.password = ''
  } catch (e) {
    const msg = e.normalizedMessage || e.response?.data?.detail || '注册失败'
    message.error(msg)
  } finally {
    loading.value = false
  }
}

async function handleResetRequest() {
  const username = resetForm.username.trim()
  if (!username) {
    message.warning('请先填写用户名')
    return
  }
  resetRequesting.value = true
  resetTip.value = ''
  try {
    const result = await requestPasswordReset({
      username,
      contact: resetForm.contact.trim()
    })
    resetTip.value = result?.message || '申请已提交，请等待管理员核验并发送验证码。'
    message.success('申请已提交')
  } catch (error) {
    message.error(error.normalizedMessage || error.response?.data?.detail || '申请提交失败')
  } finally {
    resetRequesting.value = false
  }
}

async function handleResetConfirm() {
  const username = resetForm.username.trim()
  const code = resetForm.code.trim()
  if (!username || !code) {
    message.warning('请填写用户名和验证码')
    return
  }
  if (resetForm.newPassword.length < 6) {
    message.warning('新密码至少 6 位')
    return
  }
  if (resetForm.newPassword !== resetForm.confirmPassword) {
    message.warning('两次新密码输入不一致')
    return
  }

  resetConfirming.value = true
  try {
    await verifyPasswordReset({ username, code })
    await confirmPasswordReset({
      username,
      code,
      newPassword: resetForm.newPassword
    })
    loginForm.username = username
    loginForm.password = ''
    resetForm.code = ''
    resetForm.newPassword = ''
    resetForm.confirmPassword = ''
    resetTip.value = ''
    resetVisible.value = false
    message.success('密码已重置，请使用新密码登录')
  } catch (error) {
    message.error(error.normalizedMessage || error.response?.data?.detail || '密码重置失败')
  } finally {
    resetConfirming.value = false
  }
}

</script>

<style lang="less" scoped>
@import '@/styles/variables.less';

.login-page {
  min-height: 100vh;
  display: flex;
  justify-content: center;
  align-items: center;
  background: url('/login-bg.jpg') no-repeat center center;
  background-size: cover;
  padding: 16px;
}

.login-card {
  width: 100%;
  max-width: 400px;
  background: @card-bg;
  border-radius: @border-radius-lg;
  box-shadow: @shadow-popup;
  padding: 32px 24px;
}

.login-header {
  text-align: center;
  margin-bottom: 24px;

  h1 {
    font-size: @font-size-xxl;
    color: @primary-color;
    margin-bottom: 4px;
  }
  p {
    font-size: @font-size-sm;
    color: @text-secondary;
  }
}

.login-tools {
  display: flex;
  justify-content: flex-end;
  margin: -8px 0 10px;
}

.reset-form {
  margin-top: 18px;
}

.reset-form__tip {
  margin-top: 12px;
}

</style>
