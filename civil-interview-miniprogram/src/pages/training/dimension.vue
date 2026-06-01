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

    <!-- 定向筛选 -->
    <view v-if="!readonlyMode" class="card">
      <view class="section-head">
        <text class="section-title">定向筛选（可选）</text>
      </view>
      <picker :range="examCategoryNames" :value="examCategoryIndex" @change="onExamCategoryFilterChange">
        <view class="config-row">
          <text>考试大类</text>
          <text class="config-row__value">{{ selectedExamCategoryName }}</text>
        </view>
      </picker>
      <picker :range="regionNames" :value="regionIndex" @change="onRegionFilterChange" :disabled="!regionOpts.length">
        <view class="config-row">
          <text>地区</text>
          <text class="config-row__value">{{ selectedRegionNameText }}</text>
        </view>
      </picker>
      <picker v-if="hasDirectionOpts" :range="directionNames" :value="directionIndex" @change="onDirectionFilterChange">
        <view class="config-row">
          <text>方向</text>
          <text class="config-row__value">{{ selectedDirectionNameText }}</text>
        </view>
      </picker>
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
import { hasPremiumAccess } from '../../utils/access'
import { getTrainingCategory, YEAR_OPTIONS } from '../../utils/constants'
import { DEFAULT_TARGETED_POSITION_TREE } from '../../utils/targetedOptions'
import { hideLoading, requireLogin, showLoading, toast } from '../../utils/navigation'

const billingStore = useBillingStore()
const subscriptionStore = useSubscriptionStore()
const trainingStore = useTrainingStore()
const examStore = useExamStore()
const userStore = useUserStore()
const categoryKey = ref('analysis')
const category = computed(() => getTrainingCategory(categoryKey.value))

// Targeted filter state
const selectedExamCategoryId = ref('')
const selectedRegionId = ref('')
const selectedDirectionId = ref('')
const examCatOpts = DEFAULT_TARGETED_POSITION_TREE
const examCategoryNames = computed(() => ['不限', ...examCatOpts.map(c => c.name)])
const examCategoryIndex = computed(() => {
  const idx = examCatOpts.findIndex(c => String(c.id) === String(selectedExamCategoryId.value))
  return idx >= 0 ? idx + 1 : 0
})
const selectedExamCategoryName = computed(() => {
  const cat = examCatOpts.find(c => String(c.id) === String(selectedExamCategoryId.value))
  return cat ? cat.name : '不限'
})
const selectedCatNode = computed(() =>
  selectedExamCategoryId.value ? examCatOpts.find(c => String(c.id) === String(selectedExamCategoryId.value)) || null : null
)
const regionOpts = computed(() => selectedCatNode.value?.children || [])
const regionNames = computed(() => ['不限', ...regionOpts.value.map(r => r.name)])
const regionIndex = computed(() => {
  const idx = regionOpts.value.findIndex(r => String(r.id) === String(selectedRegionId.value))
  return idx >= 0 ? idx + 1 : 0
})
const selectedRegionNameText = computed(() => {
  const r = regionOpts.value.find(r => String(r.id) === String(selectedRegionId.value))
  return r ? r.name : '不限'
})
const selectedRegNode = computed(() =>
  selectedRegionId.value ? regionOpts.value.find(r => String(r.id) === String(selectedRegionId.value)) || null : null
)
const hasDirectionOpts = computed(() => (selectedRegNode.value?.children?.length || 0) > 0)
const directionOpts = computed(() => selectedRegNode.value?.children || [])
const directionNames = computed(() => ['不限', ...directionOpts.value.map(d => d.name)])
const directionIndex = computed(() => {
  const idx = directionOpts.value.findIndex(d => String(d.id) === String(selectedDirectionId.value))
  return idx >= 0 ? idx + 1 : 0
})
const selectedDirectionNameText = computed(() => {
  const d = directionOpts.value.find(d => String(d.id) === String(selectedDirectionId.value))
  return d ? d.name : '不限'
})
const selectedDirNode = computed(() =>
  selectedDirectionId.value ? directionOpts.value.find(d => String(d.id) === String(selectedDirectionId.value)) || null : null
)
function onExamCategoryFilterChange(e) {
  const idx = Number(e.detail.value)
  selectedExamCategoryId.value = idx === 0 ? '' : (examCatOpts[idx - 1]?.id || '')
  selectedRegionId.value = ''
  selectedDirectionId.value = ''
}
function onRegionFilterChange(e) {
  const idx = Number(e.detail.value)
  selectedRegionId.value = idx === 0 ? '' : (regionOpts.value[idx - 1]?.id || '')
  selectedDirectionId.value = ''
}
function onDirectionFilterChange(e) {
  const idx = Number(e.detail.value)
  selectedDirectionId.value = idx === 0 ? '' : (directionOpts.value[idx - 1]?.id || '')
}
const hasFullAccess = computed(() => hasPremiumAccess(userStore, billingStore, subscriptionStore))
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
    const extraFilters = {}
    const cat = selectedCatNode.value
    const reg = selectedRegNode.value
    const dir = selectedDirNode.value
    if (cat) extraFilters.examCategory = cat.examCategory || cat.name
    if (reg) {
      if (reg.province) extraFilters.province = reg.province
      if (reg.examSubcategory) extraFilters.subcategory = reg.examSubcategory
      if (reg.subcategory) extraFilters.subcategory = reg.subcategory
      if (!extraFilters.subcategory) extraFilters.subcategory = reg.name
    }
    if (dir) {
      extraFilters.subcategory2 = dir.subcategory || dir.name
      if (dir.province) extraFilters.province = dir.province
    }
    const province = extraFilters.province || userStore.selectedProvince || 'national'
    const questions = await trainingStore.generate(category.value.requestDimension, 3, province, extraFilters)
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
  font-size: 48rpx;
  font-weight: 900;
  line-height: 1;
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
