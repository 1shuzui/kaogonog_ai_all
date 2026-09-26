<template>
  <view class="motion-page page" :class="motionClass" :style="motionStyle">
    <text class="page-title">找回密码</text>
    <view class="card">
      <text class="page-desc">管理员核验后发送验证码。此处不会自动发送短信或邮件；请填写可联系的方式，等待管理员联系。</text>
      <text class="page-desc">1. 提交申请 → 2. 等待管理员联系 → 3. 验证收到的验证码 → 4. 设置新密码</text>
      <text v-if="errorText" class="page-desc" role="alert">{{ errorText }}</text>
      <input v-model="form.username" class="field" placeholder="要找回的用户名" />
      <input v-model="form.contact" class="field" placeholder="可联系的手机号或邮箱" />
      <button class="secondary-button" :loading="requesting" @tap="requestCode">提交验证码申请</button>
      <text v-if="tip" class="page-desc">{{ tip }}</text>
      <input v-model="form.code" class="field" maxlength="6" placeholder="管理员发送的 6 位验证码" />
      <button class="secondary-button" :loading="verifying" :disabled="verified" @tap="verifyCode">{{ verified ? '验证码已通过，请设置新密码' : '验证验证码' }}</button>
      <text class="page-desc">验证码从管理员签发起 15 分钟内有效；失效或被锁定时，请联系管理员重新签发，使用最新收到的验证码。</text>
      <input v-model="form.newPassword" class="field" :disabled="!verified" password placeholder="新密码，至少 6 位" />
      <input v-model="confirmPassword" class="field" :disabled="!verified" password placeholder="再次输入新密码" />
      <button class="primary-button" :loading="saving" :disabled="!verified" @tap="save">设置新密码</button>
      <button class="secondary-button" @tap="back">返回登录</button>
    </view>
  </view>
</template>
<script setup>
import { usePageMotion } from '../../motion/useMotion'
const { motionClass, motionStyle } = usePageMotion()
import { computed, reactive, ref } from 'vue'
import { onLoad } from '@dcloudio/uni-app'
import { requestPasswordReset, verifyPasswordReset, confirmPasswordReset } from '../../api/auth'
import { toast } from '../../utils/navigation'

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
  } catch (error) { errorText.value = error.message || '验证失败，请重试' }
  finally { verifying.value = false }
}
onLoad(query => { form.username = query?.username || '' })
function back() { uni.redirectTo({ url: `/pages/login/index?username=${encodeURIComponent(form.username)}` }) }
async function requestCode() {
  errorText.value = ''
  if (!form.username.trim() || !form.contact.trim()) { errorText.value = '请填写用户名和可联系的手机号或邮箱'; return }
  if (requesting.value) return
  requesting.value = true
  verifiedFor.value = ''
  try {
    const result = await requestPasswordReset({ username: form.username.trim(), contact: form.contact.trim() })
    tip.value = result.message || '申请已提交，请等待管理员核验。'
  } catch (error) { errorText.value = error.message || '申请失败，请重试' } finally { requesting.value = false }
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
    toast('密码已重置，请使用新密码登录', 'success')
    back()
  } catch (error) { errorText.value = error.message || '重置失败，请重试' } finally { saving.value = false }
}
</script>
<style scoped>
.field, button { margin-top: 24rpx; }
</style>
