<template>
  <main class="reset-page card">
    <h1>找回密码</h1>
    <a-alert type="info" show-icon message="管理员核验后发送验证码" description="先提交用户名与联系方式，等待管理员核验并发送验证码。本页面不会自动发送短信或邮件。" />
    <a-form layout="vertical" style="margin-top: 24px">
      <a-form-item label="用户名"><a-input v-model:value="form.username" autocomplete="username" /></a-form-item>
      <a-form-item label="手机号或邮箱"><a-input v-model:value="form.contact" /></a-form-item>
      <a-button block :loading="requesting" @click="requestCode">提交验证码申请</a-button>
      <p role="status">{{ tip }}</p>
      <a-form-item label="管理员发送的验证码"><a-input v-model:value="form.code" :maxlength="6" autocomplete="one-time-code" /></a-form-item>
      <a-form-item label="新密码"><a-input-password v-model:value="form.newPassword" placeholder="至少 6 位" autocomplete="new-password" /></a-form-item>
      <a-form-item label="确认新密码"><a-input-password v-model:value="confirmPassword" autocomplete="new-password" /></a-form-item>
      <a-button type="primary" block :loading="saving" @click="save">核验并重置密码</a-button>
      <a-button block type="link" @click="$router.push('/login')">返回登录</a-button>
    </a-form>
  </main>
</template>
<script setup>
import { reactive, ref } from 'vue'
import { useRouter } from 'vue-router'
import { message } from 'ant-design-vue'
import { requestPasswordReset, confirmPasswordReset } from '@/api/auth'
const router = useRouter()
const form = reactive({ username: '', contact: '', code: '', newPassword: '' })
const confirmPassword = ref('')
const requesting = ref(false)
const saving = ref(false)
const tip = ref('')
async function requestCode() {
  if (!form.username.trim()) return message.warning('请输入用户名')
  if (requesting.value) return
  requesting.value = true
  try {
    const result = await requestPasswordReset({ username: form.username.trim(), contact: form.contact.trim() })
    tip.value = result.message || '申请已提交，请等待管理员核验。'
  } catch (error) { message.error(error.normalizedMessage || '申请失败，请重试') } finally { requesting.value = false }
}
async function save() {
  if (!form.username.trim() || !/^\d{6}$/.test(form.code.trim())) return message.warning('请输入用户名和 6 位验证码')
  if (form.newPassword.length < 6) return message.warning('新密码至少 6 位')
  if (form.newPassword !== confirmPassword.value) return message.warning('两次新密码输入不一致')
  if (saving.value) return
  saving.value = true
  try {
    await confirmPasswordReset({ username: form.username.trim(), code: form.code.trim(), newPassword: form.newPassword })
    message.success('密码已重置，请使用新密码登录')
    router.push('/login')
  } catch (error) { message.error(error.normalizedMessage || '重置失败，请重试') } finally { saving.value = false }
}
</script>
<style scoped>
.reset-page { max-width: 440px; margin: 48px auto; padding: 28px; }
@media (max-width: 500px) { .reset-page { margin: 16px; } }
</style>
