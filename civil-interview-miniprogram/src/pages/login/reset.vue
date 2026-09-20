<template>
  <view class="motion-page page" :class="motionClass" :style="motionStyle">
    <text class="page-title">找回密码</text>
    <view class="card">
      <text class="page-desc">管理员核验后发送验证码。此处不会自动发送短信或邮件；请填写可联系的方式，等待管理员联系。</text>
      <input v-model="form.username" class="field" placeholder="要找回的用户名" />
      <input v-model="form.contact" class="field" placeholder="可联系的手机号或邮箱" />
      <button class="secondary-button" :loading="requesting" @tap="requestCode">提交验证码申请</button>
      <text v-if="tip" class="page-desc">{{ tip }}</text>
      <input v-model="form.code" class="field" maxlength="6" placeholder="管理员发送的 6 位验证码" />
      <input v-model="form.newPassword" class="field" password placeholder="新密码，至少 6 位" />
      <input v-model="confirmPassword" class="field" password placeholder="再次输入新密码" />
      <button class="primary-button" :loading="saving" @tap="save">核验并重置密码</button>
      <button class="secondary-button" @tap="back">返回登录</button>
    </view>
  </view>
</template>
<script setup>
import { usePageMotion } from '../../motion/useMotion'
const { motionClass, motionStyle } = usePageMotion()
import { reactive, ref } from 'vue'
import { onLoad } from '@dcloudio/uni-app'
import { requestPasswordReset, confirmPasswordReset } from '../../api/auth'
import { toast } from '../../utils/navigation'

const form = reactive({ username: '', contact: '', code: '', newPassword: '' })
const confirmPassword = ref('')
const requesting = ref(false)
const saving = ref(false)
const tip = ref('')
onLoad(query => { form.username = query?.username || '' })
function back() { uni.redirectTo({ url: `/pages/login/index?username=${encodeURIComponent(form.username)}` }) }
async function requestCode() {
  if (!form.username.trim()) return toast('请输入用户名')
  if (requesting.value) return
  requesting.value = true
  try {
    const result = await requestPasswordReset({ username: form.username.trim(), contact: form.contact.trim() })
    tip.value = result.message || '申请已提交，请等待管理员核验。'
  } catch (error) { toast(error.message) } finally { requesting.value = false }
}
async function save() {
  if (!form.username.trim() || !/^\d{6}$/.test(form.code.trim())) return toast('请输入用户名和 6 位验证码')
  if (form.newPassword.length < 6) return toast('新密码至少 6 位')
  if (form.newPassword !== confirmPassword.value) return toast('两次新密码输入不一致')
  if (saving.value) return
  saving.value = true
  try {
    await confirmPasswordReset({ username: form.username.trim(), code: form.code.trim(), newPassword: form.newPassword })
    toast('密码已重置，请使用新密码登录', 'success')
    back()
  } catch (error) { toast(error.message) } finally { saving.value = false }
}
</script>
<style scoped>
.field, button { margin-top: 24rpx; }
</style>
