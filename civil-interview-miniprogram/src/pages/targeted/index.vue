<template>
  <view class="page page--tab">
    <text class="page-title">定向备面</text>
    <text class="page-desc">选择省份与岗位系统，生成更贴近报考方向的训练题。</text>

    <view v-if="readonlyMode" class="card access-card">
      <view class="section-head">
        <text class="section-title">定向备面未开通</text>
      </view>
      <text class="access-card__desc">选择省份和岗位系统后，开通套餐即可生成定向训练题并查看面试重点；也可以先体验 1 道试用题。</text>
      <view class="access-card__actions">
        <button class="secondary-button" @tap="startTrial">试用 1 题</button>
        <button class="primary-button" @tap="goPricing">开通套餐</button>
      </view>
    </view>

    <view class="card">
      <view class="section-head">
        <text class="section-title">选择省份</text>
      </view>
      <view class="chip-row">
        <view
          v-for="province in PROVINCES"
          :key="province.code"
          class="chip"
          :class="{ 'chip--active': selectedProvince === province.code }"
          @tap="selectedProvince = province.code"
        >
          {{ province.name }}
        </view>
      </view>
    </view>

    <view class="card">
      <view class="section-head">
        <text class="section-title">选择岗位系统</text>
      </view>
      <view class="chip-row">
        <view
          v-for="position in currentPositionSystems"
          :key="position.code"
          class="chip"
          :class="{ 'chip--active': selectedPosition === position.code }"
          @tap="selectedPosition = position.code"
        >
          <text class="chip__name">{{ position.name }}</text>
          <text v-if="position.desc" class="chip__desc">{{ position.desc }}</text>
        </view>
      </view>
    </view>

    <view v-if="!readonlyMode" class="targeted-actions">
      <button class="primary-button" :disabled="!canProceed" @tap="goFocus">分析面试重点</button>
      <button class="secondary-button" :disabled="!canProceed" :loading="targetedStore.generateLoading" @tap="generate">
        生成题目
      </button>
    </view>

    <view v-if="!readonlyMode && targetedStore.generatedQuestions.length">
      <view class="section-head">
        <text class="section-title">生成题目</text>
        <text class="muted" @tap="generate">重新生成</text>
      </view>
      <QuestionCard
        v-for="question in targetedStore.generatedQuestions"
        :key="question.id"
        :question="question"
        @select="startQuestion"
      />
    </view>
  </view>
</template>

<script setup>
import { computed, ref, watch } from 'vue'
import { onShow } from '@dcloudio/uni-app'
import QuestionCard from '../../components/QuestionCard.vue'
import { useBillingStore } from '../../stores/billing'
import { useExamStore } from '../../stores/exam'
import { useSubscriptionStore } from '../../stores/subscription'
import { useTargetedStore } from '../../stores/targeted'
import { useUserStore } from '../../stores/user'
import { hasPremiumAccess } from '../../utils/access'
import { POSITION_SYSTEMS, PROVINCES } from '../../utils/constants'
import { JIANGSU_TARGETED_POSITIONS } from '../../utils/jiangsuJobs'
import { hideLoading, requireLogin, showLoading, toast } from '../../utils/navigation'

const billingStore = useBillingStore()
const subscriptionStore = useSubscriptionStore()
const targetedStore = useTargetedStore()
const examStore = useExamStore()
const userStore = useUserStore()
const selectedProvince = ref(targetedStore.selectedProvince || userStore.selectedProvince || 'national')
const selectedPosition = ref(targetedStore.selectedPosition || 'general')
const currentPositionSystems = computed(() => (
  selectedProvince.value === 'jiangsu' ? JIANGSU_TARGETED_POSITIONS : POSITION_SYSTEMS
))
const canProceed = computed(() => !!selectedProvince.value && !!selectedPosition.value)
const hasFullAccess = computed(() => hasPremiumAccess(userStore, billingStore, subscriptionStore))
const readonlyMode = computed(() => !hasFullAccess.value)

function getDefaultPositionCode() {
  if (selectedProvince.value === 'jiangsu') return JIANGSU_TARGETED_POSITIONS[0]?.code || ''
  return POSITION_SYSTEMS.find((item) => item.code === 'general')?.code || POSITION_SYSTEMS[0]?.code || ''
}

watch(selectedProvince, () => {
  if (!currentPositionSystems.value.some((item) => item.code === selectedPosition.value)) {
    selectedPosition.value = getDefaultPositionCode()
  }
}, { immediate: true })

onShow(() => {
  if (!requireLogin()) return
  refreshAccessState().catch(() => null)
})

async function refreshAccessState() {
  if (!userStore.isAuthenticated) return
  await Promise.allSettled([
    userStore.loadUserInfo(),
    subscriptionStore.refresh({ skipErrorHandler: true })
  ])
}

function syncSelection() {
  targetedStore.setSelection(selectedProvince.value, selectedPosition.value)
}

function buildFocusUrl() {
  const province = encodeURIComponent(selectedProvince.value || '')
  const position = encodeURIComponent(selectedPosition.value || '')
  return `/pages/targeted/focus?province=${province}&position=${position}`
}

function goFocus() {
  if (readonlyMode.value) return
  if (!canProceed.value) return
  syncSelection()
  uni.navigateTo({ url: buildFocusUrl() })
}

async function generate() {
  if (readonlyMode.value) return
  if (!canProceed.value) {
    toast('请先选择省份和岗位系统')
    return
  }
  await refreshAccessState().catch(() => null)
  if (readonlyMode.value) {
    toast('请先开通套餐后使用定向备面')
    return
  }
  syncSelection()
  showLoading('生成题目')
  try {
    const questions = await targetedStore.fetchGeneratedQuestions(5)
    if (!questions.length) {
      toast('暂未生成题目')
      return
    }
    const fallbackCount = questions.filter((item) => item?.isProvinceFallback).length
    if (fallbackCount) {
      toast(`当前省份定向题不足，已补充 ${fallbackCount} 道国考题`)
    }
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
    }], 'targeted')
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

.targeted-actions {
  display: grid;
  grid-template-columns: minmax(0, 1fr) 220rpx;
  gap: 16rpx;
  margin-bottom: 28rpx;
}

.chip {
  display: inline-flex;
  flex-direction: column;
  align-items: flex-start;
  gap: 4rpx;
}

.chip__name,
.chip__desc {
  display: block;
}

.chip__desc {
  font-size: 21rpx;
  line-height: 1.25;
  opacity: 0.78;
}
</style>
