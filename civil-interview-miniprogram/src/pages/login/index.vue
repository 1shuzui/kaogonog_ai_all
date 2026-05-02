<template>
  <view class="login-page">
    <view class="login-card">
      <view class="login-brand">
        <text class="login-brand__title">公考面试AI测评</text>
        <text class="login-brand__subtitle">智能评分 / 精准诊断 / 高效提分</text>
      </view>

      <view class="login-tabs">
        <view
          class="login-tabs__item"
          :class="{ 'login-tabs__item--active': mode === 'login' }"
          @tap="mode = 'login'"
        >
          登录
        </view>
        <view
          class="login-tabs__item"
          :class="{ 'login-tabs__item--active': mode === 'register' }"
          @tap="mode = 'register'"
        >
          注册
        </view>
      </view>

      <view class="form-label">用户名</view>
      <input v-model="form.username" class="field" placeholder="请输入用户名" />

      <view class="form-label">密码</view>
      <input v-model="form.password" class="field" password placeholder="请输入密码" />

      <template v-if="mode === 'register'">
        <view class="form-label">确认密码</view>
        <input v-model="form.confirmPassword" class="field" password placeholder="请再次输入密码" />
      </template>

      <button class="primary-button login-submit" :loading="loading" @tap="submit">
        {{ mode === 'login' ? '登录' : '注册' }}
      </button>

      <view class="login-demo">
        <text>默认演示账号：admin / admin123</text>
      </view>
    </view>
  </view>
</template>

<script setup>
import { reactive, ref } from 'vue'
import { onShow } from '@dcloudio/uni-app'
import { useUserStore } from '../../stores/user'
import { toast } from '../../utils/navigation'

const userStore = useUserStore()
const mode = ref('login')
const loading = ref(false)
const form = reactive({
  username: '',
  password: '',
  confirmPassword: ''
})

onShow(() => {
  if (userStore.isAuthenticated) {
    uni.switchTab({ url: '/pages/home/index' })
  }
})

function validate() {
  if (!form.username.trim()) {
    toast('请输入用户名')
    return false
  }
  if (!form.password) {
    toast('请输入密码')
    return false
  }
  if (mode.value === 'register') {
    if (form.username.trim().length < 3) {
      toast('用户名至少 3 个字符')
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
  }
  return true
}

async function submit() {
  if (!validate()) return
  loading.value = true
  try {
    if (mode.value === 'login') {
      await userStore.login(form.username.trim(), form.password)
      toast('登录成功', 'success')
      uni.switchTab({ url: '/pages/home/index' })
      return
    }

    await userStore.register({
      username: form.username.trim(),
      password: form.password
    })
    toast('注册成功，请登录', 'success')
    mode.value = 'login'
    form.password = ''
    form.confirmPassword = ''
  } catch (error) {
    toast(error?.message || '操作失败')
  } finally {
    loading.value = false
  }
}
</script>

<style scoped>
.login-page {
  display: flex;
  align-items: center;
  justify-content: center;
  min-height: 100vh;
  padding: 44rpx 30rpx;
  background: linear-gradient(180deg, #e8f4fd 0%, #f0f5fa 42%, #f0f5fa 100%);
}

.login-card {
  width: 100%;
  padding: 52rpx 34rpx 36rpx;
  border-radius: 20rpx;
  background: #ffffff;
  box-shadow: 0 24rpx 60rpx rgba(21, 71, 122, 0.14);
}

.login-brand {
  display: flex;
  align-items: center;
  flex-direction: column;
  margin-bottom: 36rpx;
  text-align: center;
}

.login-brand__title {
  color: #1b5faa;
  font-size: 42rpx;
  font-weight: 800;
}

.login-brand__subtitle {
  margin-top: 10rpx;
  color: #6f7c8f;
  font-size: 25rpx;
}

.login-tabs {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 8rpx;
  margin-bottom: 24rpx;
  padding: 8rpx;
  border-radius: 14rpx;
  background: #f0f5fa;
}

.login-tabs__item {
  padding: 18rpx 0;
  border-radius: 10rpx;
  color: #6f7c8f;
  font-size: 28rpx;
  font-weight: 600;
  text-align: center;
}

.login-tabs__item--active {
  background: #ffffff;
  color: #1b5faa;
  box-shadow: 0 4rpx 12rpx rgba(23, 48, 78, 0.08);
}

.login-submit {
  margin-top: 34rpx;
}

.login-demo {
  margin-top: 24rpx;
  color: #8c8c8c;
  font-size: 23rpx;
  text-align: center;
}
</style>
