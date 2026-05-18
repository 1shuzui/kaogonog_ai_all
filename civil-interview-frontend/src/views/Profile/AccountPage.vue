<template>
  <div class="account-page page-container">
    <div class="account-header">
      <a-button type="text" @click="$router.back()">
        <LeftOutlined /> 返回
      </a-button>
      <h2>账号管理</h2>
    </div>

    <!-- 账号信息 -->
    <div class="card account-section">
      <h3>基本信息</h3>
      <div v-if="userStore.isAdmin" class="account-role-banner">
        当前账号已识别为管理员，拥有题库管理、客服后台与完整训练权限。
      </div>
      <a-form layout="vertical">
        <a-form-item label="用户名">
          <a-input :value="userStore.username" disabled />
        </a-form-item>
        <a-form-item v-if="pcLoginUsername && pcLoginUsername !== userStore.username" label="PC 登录账号">
          <a-input :value="pcLoginUsername" disabled />
        </a-form-item>
        <a-form-item label="账号角色">
          <a-input :value="userStore.isAdmin ? '管理员' : '普通用户'" disabled />
        </a-form-item>
        <a-form-item label="昵称">
          <a-input v-model:value="nickname" placeholder="请输入昵称" />
        </a-form-item>
        <a-form-item label="邮箱">
          <a-input v-model:value="email" placeholder="请输入邮箱" />
        </a-form-item>
      </a-form>
      <a-button type="primary" :loading="saving" @click="saveProfile">保存修改</a-button>
    </div>

    <!-- 修改密码 -->
    <div class="card account-section">
      <h3>修改密码</h3>
      <a-form layout="vertical">
        <a-form-item label="当前密码">
          <a-input-password v-model:value="oldPassword" placeholder="请输入当前密码" />
        </a-form-item>
        <a-form-item label="新密码">
          <a-input-password v-model:value="newPassword" placeholder="请输入新密码（至少6位）" />
        </a-form-item>
        <a-form-item label="确认新密码">
          <a-input-password v-model:value="confirmPassword" placeholder="请再次输入新密码" />
        </a-form-item>
      </a-form>
      <a-button type="primary" :loading="changingPwd" @click="changePassword">修改密码</a-button>
    </div>

    <div class="card account-section">
      <h3>协议与隐私</h3>
      <p class="data-hint">
        当前版本：{{ terms.latestVersion || '-' }}
        <span v-if="terms.agreedAt">，最近同意时间：{{ formatTime(terms.agreedAt) }}</span>
      </p>
      <div class="agreement-actions">
        <a-button @click="$router.push('/legal')">查看协议正文</a-button>
        <a-button
          v-if="terms.needsUpdate"
          type="primary"
          :loading="agreeingTerms"
          @click="agreeLatestTerms"
        >
          同意最新版
        </a-button>
      </div>
    </div>

    <div class="card account-section">
      <h3>微信快捷登录绑定</h3>
      <p class="data-hint">
        小程序端绑定当前微信后，微信快捷登录会进入本账号；PC 端使用本账号密码登录，即可同步题库、历史、权益和设置。
      </p>
      <a-tag :color="wechatMiniBound ? 'green' : 'default'">
        {{ wechatMiniBound ? '小程序微信已绑定' : '小程序微信未绑定' }}
      </a-tag>
      <p class="data-hint account-section__hint">
        {{ pcLoginUsername ? `PC 登录账号：${pcLoginUsername}` : '如需绑定或创建 PC 登录账号，请打开小程序「我的 - 账号安全」完成。' }}
      </p>
    </div>

    <!-- 数据管理 -->
    <div class="card account-section">
      <h3>数据管理</h3>
      <p class="data-hint">清除本地缓存数据（包括收藏、训练进度等）</p>
      <a-popconfirm
        title="确认清除本地数据？"
        description="这会删除本机缓存的收藏、训练进度、题库筛选和本地反馈记录，不会删除服务器账号数据。"
        ok-text="确认清除"
        cancel-text="取消"
        @confirm="clearLocalData"
      >
        <a-button danger>清除本地数据</a-button>
      </a-popconfirm>
    </div>
  </div>
</template>

<script setup>
import { computed, reactive, ref, onMounted } from 'vue'
import { LeftOutlined } from '@ant-design/icons-vue'
import { useUserStore } from '@/stores/user'
import { message } from 'ant-design-vue'
import http from '@/api/index'
import { agreeTerms, getTermsStatus } from '@/api/user'

const userStore = useUserStore()

const nickname = ref('')
const email = ref('')
const saving = ref(false)
const oldPassword = ref('')
const newPassword = ref('')
const confirmPassword = ref('')
const changingPwd = ref(false)
const agreeingTerms = ref(false)
const terms = reactive({
  hasAgreed: false,
  agreedVersion: '',
  latestVersion: '',
  updatedAt: '',
  effectiveAt: '',
  agreedAt: '',
  needsUpdate: false
})
const wechatMiniBound = computed(() => userStore.userInfo?.accountBindings?.wechatMiniBound === true)
const pcLoginUsername = computed(() => userStore.userInfo?.accountLogin?.pcLoginUsername || '')

onMounted(async () => {
  await userStore.loadUserInfo()
  nickname.value = userStore.userInfo?.name || ''
  email.value = userStore.email || ''
  await loadTermsStatus()
})

async function loadTermsStatus() {
  try {
    Object.assign(terms, await getTermsStatus({ skipErrorHandler: true }))
  } catch {
    // ignore
  }
}

async function saveProfile() {
  saving.value = true
  try {
    await http.put('/user/profile', {
      full_name: nickname.value,
      email: email.value
    })
    // 更新本地 store 中的用户信息
    userStore.userInfo.name = nickname.value
    userStore.email = email.value
    message.success('信息已更新')
  } catch {
    // error handled by interceptor
  } finally {
    saving.value = false
  }
}

async function changePassword() {
  if (!oldPassword.value || !newPassword.value) {
    message.warning('请填写完整的密码信息')
    return
  }
  if (newPassword.value.length < 6) {
    message.warning('新密码至少6位')
    return
  }
  if (newPassword.value !== confirmPassword.value) {
    message.warning('两次输入的新密码不一致')
    return
  }
  changingPwd.value = true
  try {
    await http.put('/user/password', {
      old_password: oldPassword.value,
      new_password: newPassword.value
    })
    message.success('密码修改成功')
    oldPassword.value = ''
    newPassword.value = ''
    confirmPassword.value = ''
  } catch {
    // error handled by interceptor
  } finally {
    changingPwd.value = false
  }
}

function clearLocalData() {
  const prefixes = [
    'civil_favorites',
    'civil_training_progress',
    'civil_support_feedback_records',
    'civil_selected_province',
    'civil_selected_province_confirmed',
    'civil_user_preferences',
    'civil_billing_state'
  ]
  Object.keys(localStorage)
    .filter((key) => prefixes.some((prefix) => key === prefix || key.startsWith(`${prefix}:`)))
    .forEach((key) => localStorage.removeItem(key))
  message.success('本地数据已清除')
}

async function agreeLatestTerms() {
  if (!terms.latestVersion) return
  agreeingTerms.value = true
  try {
    await agreeTerms(terms.latestVersion)
    await loadTermsStatus()
    await userStore.loadUserInfo()
    message.success('已同意最新版协议')
  } catch {
    // handled by interceptor
  } finally {
    agreeingTerms.value = false
  }
}

function formatTime(value = '') {
  const date = value ? new Date(value) : null
  if (!date || Number.isNaN(date.getTime())) return ''
  return `${date.getFullYear()}-${String(date.getMonth() + 1).padStart(2, '0')}-${String(date.getDate()).padStart(2, '0')} ${String(date.getHours()).padStart(2, '0')}:${String(date.getMinutes()).padStart(2, '0')}`
}
</script>

<style lang="less" scoped>
@import '@/styles/variables.less';

.account-header {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 16px;

  h2 {
    font-size: @font-size-xl;
    color: @text-primary;
    margin: 0;
  }
}

.account-section {
  padding: 16px;
  margin-bottom: 12px;

  h3 {
    font-size: @font-size-lg;
    color: @text-primary;
    margin-bottom: 12px;
  }
}

.account-role-banner {
  margin-bottom: 16px;
  padding: 10px 12px;
  border-radius: @border-radius;
  background: rgba(27, 95, 170, 0.08);
  color: @primary-color;
  font-size: @font-size-sm;
}

.data-hint {
  font-size: @font-size-sm;
  color: @text-secondary;
  margin-bottom: 12px;
}

.agreement-actions {
  display: flex;
  gap: 10px;
  flex-wrap: wrap;
}
</style>
