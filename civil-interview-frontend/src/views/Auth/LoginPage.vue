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
            <div class="legal-hint">
              登录即表示您已阅读并同意
              <a-button type="link" size="small" @click="$router.push('/legal')">《用户协议》与《隐私协议》</a-button>
            </div>
            <div class="login-tools">
              <a-button type="link" size="small" @click="resetModalVisible = true">忘记密码？</a-button>
            </div>
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
            <a-button
              block
              size="large"
              :disabled="!wechatWebLogin.configured"
              @click="handleWechatWebLogin"
            >
              <template #icon><WechatOutlined /></template>
              {{ wechatWebLogin.configured ? '微信扫码登录' : '微信扫码登录待配置' }}
            </a-button>
            <div v-if="!wechatWebLogin.configured" class="wechat-login-note">
              {{ wechatWebLogin.message }}
            </div>
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
              <a-checkbox v-model:checked="registerForm.agreedTerms">
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

      <a-modal
        v-model:open="resetModalVisible"
        title="找回密码"
        ok-text="重置密码"
        cancel-text="取消"
        :confirm-loading="resetLoading"
        @ok="handlePasswordResetConfirm"
      >
        <a-form layout="vertical">
          <a-form-item label="用户名">
            <a-input v-model:value="resetForm.username" placeholder="请输入要找回的用户名" />
          </a-form-item>
          <a-form-item label="邮箱或手机号（可选）">
            <a-input v-model:value="resetForm.contact" placeholder="如账号绑定过邮箱，可填写用于校验" />
          </a-form-item>
          <a-space style="margin-bottom: 12px">
            <a-button size="small" :loading="resetRequesting" @click="handlePasswordResetRequest">
              获取验证码
            </a-button>
            <a-button size="small" :disabled="!resetForm.code" @click="handlePasswordResetVerify">
              验证
            </a-button>
          </a-space>
          <a-alert
            v-if="resetTip"
            :message="resetTip"
            type="info"
            show-icon
            style="margin-bottom: 12px"
          />
          <a-form-item label="验证码">
            <a-input v-model:value="resetForm.code" placeholder="请输入验证码" />
          </a-form-item>
          <a-form-item label="新密码">
            <a-input-password v-model:value="resetForm.newPassword" placeholder="至少 6 位" />
          </a-form-item>
          <a-form-item label="确认新密码">
            <a-input-password v-model:value="resetForm.confirmPassword" placeholder="请再次输入新密码" />
          </a-form-item>
        </a-form>
      </a-modal>
    </div>
  </div>
</template>

<script setup>
import { ref, reactive, h, onMounted } from 'vue'
import { useRoute } from 'vue-router'
import { message } from 'ant-design-vue'
import { UserOutlined, LockOutlined, WechatOutlined } from '@ant-design/icons-vue'
import { useUserStore } from '@/stores/user'
import {
  confirmPasswordReset,
  getWechatWebLoginUrl,
  requestPasswordReset,
  verifyPasswordReset
} from '@/api/auth'

const route = useRoute()
const userStore = useUserStore()

const activeTab = ref('login')
const loading = ref(false)
const resetModalVisible = ref(false)
const resetLoading = ref(false)
const resetRequesting = ref(false)
const resetTip = ref('')
const wechatWebLogin = reactive({
  configured: false,
  loginUrl: '',
  message: 'PC 微信扫码登录未启用：缺少微信开放平台网站应用资料。'
})
const loginFormRef = ref(null)
const registerFormRef = ref(null)

const loginForm = reactive({ username: '', password: '' })
const registerForm = reactive({ username: '', password: '', confirmPassword: '', agreedTerms: false })
const resetForm = reactive({
  username: '',
  contact: '',
  code: '',
  newPassword: '',
  confirmPassword: ''
})

const loginRules = {
  username: [{ required: true, message: '请输入用户名', trigger: 'blur' }],
  password: [{ required: true, message: '请输入密码', trigger: 'blur' }]
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

function normalizeRedirectTarget(value) {
  const raw = Array.isArray(value) ? value[0] : value
  if (typeof raw !== 'string' || !raw.startsWith('/') || raw.startsWith('//')) {
    return '/'
  }
  return raw || '/'
}

async function loadWechatWebLoginConfig() {
  try {
    const config = await getWechatWebLoginUrl()
    wechatWebLogin.configured = !!config?.configured
    wechatWebLogin.loginUrl = config?.loginUrl || ''
    wechatWebLogin.message = config?.message || wechatWebLogin.message
  } catch {
    wechatWebLogin.configured = false
  }
}

function handleWechatWebLogin() {
  if (!wechatWebLogin.configured || !wechatWebLogin.loginUrl) {
    message.info(wechatWebLogin.message)
    return
  }
  window.location.href = wechatWebLogin.loginUrl
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
    registerForm.agreedTerms = false
  } catch (e) {
    const msg = e.normalizedMessage || e.response?.data?.detail || '注册失败'
    message.error(msg)
  } finally {
    loading.value = false
  }
}

async function handlePasswordResetRequest() {
  if (!resetForm.username.trim()) {
    message.warning('请先填写用户名')
    return
  }
  resetRequesting.value = true
  resetTip.value = ''
  try {
    const result = await requestPasswordReset({
      username: resetForm.username.trim(),
      contact: resetForm.contact.trim()
    })
    resetTip.value = result?.debugCode
      ? `验证码：${result.debugCode}。短信服务尚未接入时，请由管理员转交该验证码。`
      : (result?.message || '验证码已发送，请查收。')
    message.success('验证码已生成')
  } catch (e) {
    message.error(e.normalizedMessage || e.response?.data?.detail || '验证码生成失败')
  } finally {
    resetRequesting.value = false
  }
}

async function handlePasswordResetVerify() {
  if (!resetForm.username.trim() || !resetForm.code.trim()) {
    message.warning('请填写用户名和验证码')
    return
  }
  try {
    await verifyPasswordReset({
      username: resetForm.username.trim(),
      code: resetForm.code.trim()
    })
    message.success('验证码验证通过')
  } catch (e) {
    message.error(e.normalizedMessage || e.response?.data?.detail || '验证码验证失败')
  }
}

async function handlePasswordResetConfirm() {
  if (!resetForm.username.trim() || !resetForm.code.trim()) {
    message.warning('请填写用户名和验证码')
    return
  }
  if (resetForm.newPassword.length < 6) {
    message.warning('新密码至少 6 位')
    return
  }
  if (resetForm.newPassword !== resetForm.confirmPassword) {
    message.warning('两次输入的新密码不一致')
    return
  }
  resetLoading.value = true
  try {
    await confirmPasswordReset({
      username: resetForm.username.trim(),
      code: resetForm.code.trim(),
      newPassword: resetForm.newPassword
    })
    message.success('密码已重置，请登录')
    loginForm.username = resetForm.username.trim()
    loginForm.password = ''
    resetModalVisible.value = false
    resetForm.code = ''
    resetForm.newPassword = ''
    resetForm.confirmPassword = ''
    resetTip.value = ''
  } catch (e) {
    message.error(e.normalizedMessage || e.response?.data?.detail || '密码重置失败')
  } finally {
    resetLoading.value = false
  }
}

onMounted(() => {
  loadWechatWebLoginConfig()
})
</script>

<style scoped>
.legal-hint {
  margin-bottom: 12px;
  color: #8c8c8c;
  font-size: 13px;
}
</style>

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

.wechat-login-note {
  margin-top: 8px;
  color: @text-secondary;
  font-size: @font-size-xs;
  line-height: 1.6;
}
</style>
