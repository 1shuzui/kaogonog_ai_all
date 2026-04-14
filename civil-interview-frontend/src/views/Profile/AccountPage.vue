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
      <a-form layout="vertical">
        <a-form-item label="用户名">
          <a-input :value="userStore.username" disabled />
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

    <!-- 数据管理 -->
    <div class="card account-section">
      <h3>数据管理</h3>
      <p class="data-hint">清除本地缓存数据（包括收藏、训练进度等）</p>
      <a-button danger @click="clearLocalData">清除本地数据</a-button>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { LeftOutlined } from '@ant-design/icons-vue'
import { useUserStore } from '@/stores/user'
import { useExamStore } from '@/stores/exam'
import { message } from 'ant-design-vue'
import http from '@/api/index'

const userStore = useUserStore()
const examStore = useExamStore()

const nickname = ref('')
const email = ref('')
const saving = ref(false)
const oldPassword = ref('')
const newPassword = ref('')
const confirmPassword = ref('')
const changingPwd = ref(false)

onMounted(async () => {
  await userStore.loadUserInfo()
  nickname.value = userStore.userInfo?.name || ''
  email.value = userStore.email || ''
})

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
  const keys = ['civil_favorites', 'civil_training_progress']
  keys.forEach(key => localStorage.removeItem(key))
  sessionStorage.removeItem('targeted_question')
  sessionStorage.removeItem('training_question')
  examStore.clearPersistedSession()
  message.success('本地数据已清除')
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

.data-hint {
  font-size: @font-size-sm;
  color: @text-secondary;
  margin-bottom: 12px;
}
</style>
