<template>
  <view class="page">
    <text class="page-title">模考准备</text>
    <text class="page-desc">小程序端支持录音作答，也可以直接输入文字作答后提交评分。</text>

    <view class="card">
      <view class="section-head">
        <text class="section-title">练习配置</text>
      </view>

      <view class="config-row">
        <text>题目数量</text>
        <view class="stepper">
          <button class="stepper__button" @tap="decreaseCount">-</button>
          <text class="stepper__value">{{ count }}</text>
          <button class="stepper__button" @tap="increaseCount">+</button>
        </view>
      </view>

      <view class="config-row">
        <text>练习模式</text>
      </view>
      <view class="mode-grid">
        <view class="mode-card" :class="{ 'mode-card--active': mode === 'free' }" @tap="mode = 'free'">
          <text class="mode-card__title">自由练习</text>
          <text class="mode-card__desc">适合单题拆解和即时复盘</text>
        </view>
        <view class="mode-card" :class="{ 'mode-card--active': mode === 'mock' }" @tap="mode = 'mock'">
          <text class="mode-card__title">模拟面试</text>
          <text class="mode-card__desc">按准备和作答计时推进</text>
        </view>
      </view>
    </view>

    <view class="card tips-card">
      <text class="tips-card__title">开考前检查</text>
      <text class="tips-card__line">保持环境安静，授权麦克风后可录制作答音频。</text>
      <text class="tips-card__line">真机调试时，后端地址需使用手机可访问的域名或局域网 IP。</text>
    </view>

    <button class="primary-button" :loading="loading" @tap="startPractice">进入考场</button>
  </view>
</template>

<script setup>
import { ref } from 'vue'
import { onLoad } from '@dcloudio/uni-app'
import { useExamStore } from '../../stores/exam'
import { useQuestionBankStore } from '../../stores/questionBank'
import { useUserStore } from '../../stores/user'
import { hideLoading, requireLogin, showLoading, toast } from '../../utils/navigation'

const examStore = useExamStore()
const questionBankStore = useQuestionBankStore()
const userStore = useUserStore()
const count = ref(3)
const mode = ref('free')
const loading = ref(false)
const trial = ref(false)

onLoad((query) => {
  trial.value = String(query?.trial || '') === '1'
  if (trial.value) count.value = 1
})

function decreaseCount() {
  count.value = Math.max(1, count.value - 1)
}

function increaseCount() {
  if (trial.value) return
  count.value = Math.min(5, count.value + 1)
}

async function startPractice() {
  if (!requireLogin()) return
  loading.value = true
  showLoading('抽取题目')
  try {
    const questions = await questionBankStore.fetchRandom({
      province: userStore.selectedProvince,
      count: count.value
    })
    if (!questions.length) {
      toast('当前筛选条件暂无题目')
      return
    }
    await examStore.startFromQuestions(questions.slice(0, count.value), mode.value)
    uni.navigateTo({ url: '/pages/exam/room' })
  } catch (error) {
    toast(error?.message || '进入考场失败')
  } finally {
    loading.value = false
    hideLoading()
  }
}
</script>

<style scoped>
.config-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 18rpx 0;
  color: #2a3648;
  font-size: 28rpx;
  font-weight: 600;
}

.stepper {
  display: flex;
  align-items: center;
  overflow: hidden;
  border: 1rpx solid #d9e3ef;
  border-radius: 12rpx;
}

.stepper__button {
  width: 76rpx;
  height: 68rpx;
  border-radius: 0;
  background: #f6f8fb;
  color: #1b5faa;
  font-size: 34rpx;
}

.stepper__value {
  width: 86rpx;
  color: #1a1a2e;
  font-size: 30rpx;
  font-weight: 800;
  text-align: center;
}

.mode-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 16rpx;
  margin-top: 8rpx;
}

.mode-card {
  min-height: 150rpx;
  padding: 22rpx;
  border: 1rpx solid #d9e3ef;
  border-radius: 16rpx;
  background: #ffffff;
}

.mode-card--active {
  border-color: #1b5faa;
  background: #e8f4fd;
}

.mode-card__title,
.mode-card__desc {
  display: block;
}

.mode-card__title {
  color: #1a1a2e;
  font-size: 29rpx;
  font-weight: 800;
}

.mode-card__desc {
  margin-top: 10rpx;
  color: #6f7c8f;
  font-size: 23rpx;
  line-height: 1.5;
}

.tips-card__title,
.tips-card__line {
  display: block;
}

.tips-card__title {
  color: #1a1a2e;
  font-size: 30rpx;
  font-weight: 800;
}

.tips-card__line {
  margin-top: 12rpx;
  color: #6f7c8f;
  font-size: 24rpx;
  line-height: 1.6;
}
</style>
