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
  </div>
</template>

<script setup>
import { ref, reactive, h } from 'vue'
import { useRoute } from 'vue-router'
import { message } from 'ant-design-vue'
import { UserOutlined, LockOutlined } from '@ant-design/icons-vue'
import { useUserStore } from '@/stores/user'

const route = useRoute()
const userStore = useUserStore()

const activeTab = ref('login')
const loading = ref(false)
const loginFormRef = ref(null)
const registerFormRef = ref(null)
const AGREED_TERMS_STORAGE_KEY = 'civil_agreed_terms_version'
const AGREED_TERMS_VERSION = '2026-05-12'

const loginForm = reactive({ username: '', password: '', agreedTerms: false })
const registerForm = reactive({ username: '', password: '', confirmPassword: '', agreedTerms: false })

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

</style>
