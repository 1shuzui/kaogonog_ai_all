<template>
  <main class="reset-page card">
    <h1>找回密码</h1>
    <a-alert type="info" show-icon message="管理员核验后发送验证码" description="先提交用户名与联系方式，等待管理员核验并发送验证码。本页面不会自动发送短信或邮件。" />
    <p>1. 提交申请 → 2. 等待管理员联系 → 3. 验证收到的验证码 → 4. 设置新密码</p>
    <a-alert v-if="errorText" type="error" :message="errorText" show-icon />
    <a-form layout="vertical" style="margin-top: 24px">
      <a-form-item label="用户名"><a-input v-model:value="form.username" autocomplete="username" /></a-form-item>
      <a-form-item label="手机号或邮箱"><a-input v-model:value="form.contact" /></a-form-item>
      <a-button block :loading="requesting" @click="requestCode">提交验证码申请</a-button>
      <p role="status">{{ tip }}</p>
      <a-form-item label="管理员发送的验证码"><a-input v-model:value="form.code" :maxlength="6" autocomplete="one-time-code" /></a-form-item>
      <a-button block :loading="verifying" :disabled="verified" @click="verifyCode">{{ verified ? '验证码已通过，请设置新密码' : '验证验证码' }}</a-button>
      <p>验证码从管理员签发起 15 分钟内有效；失效或被锁定时，请联系管理员重新签发，使用最新收到的验证码。</p>
      <a-form-item label="新密码"><a-input-password v-model:value="form.newPassword" :disabled="!verified" placeholder="至少 6 位" autocomplete="new-password" /></a-form-item>
      <a-form-item label="确认新密码"><a-input-password v-model:value="confirmPassword" :disabled="!verified" autocomplete="new-password" /></a-form-item>
      <a-button type="primary" block :loading="saving" :disabled="!verified" @click="save">设置新密码</a-button>
      <a-button block type="link" @click="$router.push('/login')">返回登录</a-button>
    </a-form>
  </main>
</template>
<script setup>
import { computed, reactive, ref } from 'vue'
import { useRouter } from 'vue-router'
import { message } from 'ant-design-vue'
import { requestPasswordReset, verifyPasswordReset, confirmPasswordReset } from '@/api/auth'
const router = useRouter()
const form = reactive({ username: '', contact: '', code: '', newPassword: '' })
const confirmPassword = ref('')
const requesting = ref(false)
const saving = ref(false)
const tip = ref('')
const errorText = ref('')
const verifying = ref(false)
const verifiedFor = ref('')
const verificationKey = computed(() => JSON.stringify([form.username.trim(), form.code.trim()]))
const verified = computed(() => verifiedFor.value === verificationKey.value)
async function verifyCode() {
  errorText.value = ''
  if (!form.username.trim() || !/^\d{6}$/.test(form.code.trim())) { errorText.value = '请输入用户名和 6 位验证码'; return }
  if (verifying.value) return
  verifying.value = true
  const key = verificationKey.value
  try {
    await verifyPasswordReset({ username: form.username.trim(), code: form.code.trim() })
    verifiedFor.value = key
  } catch (error) { errorText.value = error.normalizedMessage || '验证失败，请重试' }
  finally { verifying.value = false }
}
async function requestCode() {
  errorText.value = ''
  if (!form.username.trim() || !form.contact.trim()) { errorText.value = '请填写用户名和可联系的手机号或邮箱'; return }
  if (requesting.value) return
  requesting.value = true
  verifiedFor.value = ''
  try {
    const result = await requestPasswordReset({ username: form.username.trim(), contact: form.contact.trim() })
    tip.value = result.message || '申请已提交，请等待管理员核验。'
  } catch (error) { errorText.value = error.normalizedMessage || '申请失败，请重试' } finally { requesting.value = false }
}
async function save() {
  errorText.value = ''
  if (!verified.value) { errorText.value = '请先验证验证码'; return }
  if (form.newPassword.length < 6) { errorText.value = '新密码至少 6 位'; return }
  if (form.newPassword !== confirmPassword.value) { errorText.value = '两次新密码输入不一致'; return }
  if (saving.value) return
  saving.value = true
  try {
    await confirmPasswordReset({ username: form.username.trim(), code: form.code.trim(), newPassword: form.newPassword })
    message.success('密码已重置，请使用新密码登录')
    router.push('/login')
  } catch (error) { errorText.value = error.normalizedMessage || '重置失败，请重试' } finally { saving.value = false }
}
</script>
<style scoped>
.reset-page { max-width: 440px; margin: 48px auto; padding: 28px; }
@media (max-width: 500px) { .reset-page { margin: 16px; } }
</style>
