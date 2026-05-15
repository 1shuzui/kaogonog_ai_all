<template>
  <view class="page">
    <view v-if="readonlyMode" class="card access-card">
      <view class="section-head">
        <text class="section-title">专项训练未开通</text>
      </view>
      <text class="access-card__desc">开通套餐后可以按题型生成训练题；也可以先体验 1 道试用题，确认录音、转写和评分流程。</text>
      <view class="access-card__actions">
        <button class="secondary-button" @tap="startTrial">试用 1 题</button>
        <button class="primary-button" @tap="goPricing">开通套餐</button>
      </view>
    </view>

    <view class="dimension-hero card">
      <view class="dimension-hero__icon" :style="{ background: category.tone }">{{ category.icon }}</view>
      <view>
        <text class="dimension-hero__title">{{ category.name }}</text>
        <text class="dimension-hero__desc">{{ category.tip }}</text>
      </view>
    </view>

    <view class="card">
      <view class="section-head">
        <text class="section-title">训练进度</text>
      </view>
      <StatGrid :items="progressItems" />
    </view>

    <button v-if="!readonlyMode" class="primary-button" :loading="trainingStore.generating" @tap="generate">生成训练题</button>

    <view v-if="!readonlyMode && trainingStore.generatedQuestions.length" class="generated-list">
      <view class="section-head generated-list__head">
        <text class="section-title">训练题</text>
      </view>
      <QuestionCard
        v-for="question in trainingStore.generatedQuestions"
        :key="question.id"
        :question="question"
        @select="startQuestion"
      />
    </view>
  </view>
</template>

<script setup>
import { computed, ref } from 'vue'
import { onLoad } from '@dcloudio/uni-app'
import QuestionCard from '../../components/QuestionCard.vue'
import StatGrid from '../../components/StatGrid.vue'
import { useBillingStore } from '../../stores/billing'
import { useExamStore } from '../../stores/exam'
import { useSubscriptionStore } from '../../stores/subscription'
import { useTrainingStore } from '../../stores/training'
import { useUserStore } from '../../stores/user'
import { getTrainingCategory } from '../../utils/constants'
import { hideLoading, requireLogin, showLoading, toast } from '../../utils/navigation'

const billingStore = useBillingStore()
const subscriptionStore = useSubscriptionStore()
const trainingStore = useTrainingStore()
const examStore = useExamStore()
const userStore = useUserStore()
const categoryKey = ref('analysis')
const category = computed(() => getTrainingCategory(categoryKey.value))
const hasFullAccess = computed(() => (
  userStore.isAdmin
  || billingStore.isPaid
  || subscriptionStore.hasPremiumAccess
  || userStore.userInfo?.billing?.isPaid === true
  || userStore.userInfo?.permissions?.canAccessPremiumModules === true
))
const readonlyMode = computed(() => !hasFullAccess.value)
const progress = computed(() => trainingStore.getDimensionProgress(categoryKey.value))
const progressItems = computed(() => [
  { label: '练习次数', value: progress.value.attempts || 0 },
  { label: '最佳分', value: progress.value.bestScore || 0 },
  {
    label: '平均分',
    value: progress.value.attempts ? Math.round(progress.value.totalScore / progress.value.attempts) : 0
  }
])

onLoad((query) => {
  if (!requireLogin()) return
  categoryKey.value = query?.key || 'analysis'
  refreshAccessState().catch(() => null)
})

async function refreshAccessState() {
  if (!userStore.isAuthenticated) return
  await Promise.allSettled([
    userStore.loadUserInfo(),
    subscriptionStore.refresh({ skipErrorHandler: true })
  ])
}

async function generate() {
  if (readonlyMode.value) return
  await refreshAccessState().catch(() => null)
  if (readonlyMode.value) {
    toast('请先开通套餐后使用专项训练')
    return
  }
  showLoading('生成训练题')
  try {
    const questions = await trainingStore.generate(category.value.requestDimension, 3)
    if (!questions.length) toast('暂未生成题目')
  } catch (error) {
    toast(error?.message || '生成失败')
  } finally {
    hideLoading()
  }
}

async function startQuestion(question) {
  if (readonlyMode.value) return
  showLoading('创建考场')
  try {
    const prefs = userStore.preferences || {}
    await examStore.startFromQuestions([{
      ...question,
      prepTime: Number(prefs.defaultPrepTime || question?.prepTime || 90),
      answerTime: Number(prefs.defaultAnswerTime || question?.answerTime || 180)
    }], `training:${categoryKey.value}`)
    uni.navigateTo({ url: '/pages/exam/room' })
  } catch (error) {
    toast(error?.message || '无法开始练习')
  } finally {
    hideLoading()
  }
}

function goPricing() {
  uni.navigateTo({ url: '/pages/pricing/index' })
}

function startTrial() {
  uni.navigateTo({ url: '/pages/exam/prepare?trial=1' })
}
</script>

<style scoped>
.access-card {
  border-color: #bfd7ef;
  background: #f4f9fe;
}

.access-card__desc {
  display: block;
  color: #5f6f83;
  font-size: 24rpx;
  line-height: 1.6;
}

.access-card__actions {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 16rpx;
  margin-top: 22rpx;
}

.dimension-hero {
  display: grid;
  grid-template-columns: 100rpx minmax(0, 1fr);
  gap: 22rpx;
  align-items: center;
}

.dimension-hero__icon {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 100rpx;
  height: 100rpx;
  border-radius: 20rpx;
  color: #1b5faa;
  font-size: 38rpx;
  font-weight: 900;
}

.dimension-hero__title,
.dimension-hero__desc {
  display: block;
}

.dimension-hero__title {
  color: #1a1a2e;
  font-size: 36rpx;
  font-weight: 800;
}

.dimension-hero__desc {
  margin-top: 8rpx;
  color: #6f7c8f;
  font-size: 24rpx;
  line-height: 1.5;
}

.generated-list__head {
  margin-top: 28rpx;
}
</style>
