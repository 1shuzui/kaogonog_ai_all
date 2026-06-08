<!--
这个小程序页面让用户按考试体系、地区和方向选择定向备面；方向可以不限，开始练习前再要求登录和权益。

@param: 无；页面运行时从 props、路由参数、Pinia 状态和用户点击中拿数据。
@return: 渲染当前业务界面，并把按钮、表单或跳转事件交给既有流程处理。
@raises: 不主动抛业务异常；接口失败、未登录和权限不足由请求层或页面提示承接。
-->
<template>
  <view class="page page--tab">
    <text class="page-title">定向备面</text>
    <text class="page-desc">按真实考试体系、地区来源和岗位方向选择，生成更贴近报考方向的训练题。</text>

    <view v-if="readonlyMode" class="card access-card">
      <view class="section-head">
        <text class="section-title">定向备面未开通</text>
      </view>
      <text class="access-card__desc">选择考试方向后，开通套餐即可生成定向训练题并查看面试重点；也可以先体验 1 道试用题。</text>
      <view class="access-card__actions">
        <button class="secondary-button" @tap="startTrial">试用 1 题</button>
        <button class="primary-button" @tap="goPricing">开通套餐</button>
      </view>
    </view>

    <view class="card picker-card">
      <view class="section-head">
        <text class="section-title">选择考试方向</text>
      </view>
      <LightSelector title="考试体系" :options="categoryNames" :value="categoryIndex" @change="onCategoryPickerChange">
        <view class="picker-row">
          <text>考试体系</text>
          <text class="picker-row__value">{{ selectedCategoryName }}</text>
        </view>
      </LightSelector>
      <LightSelector :title="regionLevelLabel" :options="regionNames" :value="regionIndex" @change="onRegionPickerChange">
        <view class="picker-row">
          <text>{{ regionLevelLabel }}</text>
          <text class="picker-row__value">{{ selectedRegionName }}</text>
        </view>
      </LightSelector>
      <LightSelector v-if="hasDirectionLevel" :title="directionLevelLabel" :options="directionNames" :value="directionIndex" @change="onDirectionPickerChange">
        <view class="picker-row">
          <text>{{ directionLevelLabel }}</text>
          <text class="picker-row__value">{{ selectedDirectionName }}</text>
        </view>
      </LightSelector>
      <view class="picker-row picker-row--year" @tap="showYearPicker = true">
        <text>年份</text>
        <text class="picker-row__value">{{ yearLabel }}</text>
      </view>
      <text v-if="activeTarget" class="picker-summary">
        当前选择：{{ selectedPathLabel }}
      </text>
      <view v-if="selectedModeHints.length" class="mode-hints">
        <text v-for="hint in selectedModeHints" :key="hint" class="mode-hint">{{ hint }}</text>
      </view>
    </view>

    <view v-if="!readonlyMode" class="targeted-actions">
      <button class="primary-button" :disabled="!canProceed" @tap="goFocus">分析面试重点</button>
      <button class="secondary-button" :disabled="!canProceed" :loading="targetedStore.generateLoading" @tap="generate">
        生成题目
      </button>
    </view>

    <view v-if="!readonlyMode && targetedStore.generatedQuestions.length">
      <view class="generated-start card">
        <view>
          <text class="generated-start__title">已为当前考试方向准备 {{ targetedStore.generatedQuestions.length }} 道练习题</text>
          <text class="generated-start__desc">先核对题目，再进入专项练习。</text>
        </view>
        <button class="primary-button" @tap="startGeneratedPractice">开始练习</button>
      </view>
      <view class="section-head">
        <text class="section-title">生成题目</text>
        <text class="muted" @tap="generate">重新生成</text>
      </view>
      <QuestionCard
        v-for="question in targetedStore.generatedQuestions"
        :key="question.id"
        :question="question"
        :show-rich-content="true"
        :show-meta-tags="true"
        :collapsed-height="224"
        @select="startQuestion"
      />
    </view>

    <view v-if="showYearPicker" class="year-overlay" @tap="showYearPicker = false">
      <view class="year-modal card" @tap.stop>
        <view class="section-head">
          <text class="section-title">选择年份</text>
          <text class="muted" @tap="showYearPicker = false">完成</text>
        </view>
        <checkbox-group @change="onYearChange">
          <label v-for="opt in yearOptions" :key="opt.value" class="year-checkbox">
            <checkbox :value="opt.value" :checked="opt.checked" />
            <text>{{ opt.value }}</text>
          </label>
        </checkbox-group>
      </view>
    </view>
  </view>
</template>

<script setup>
import { computed, ref, watch } from 'vue'
import { onShow } from '@dcloudio/uni-app'
import LightSelector from '../../components/LightSelector.vue'
import QuestionCard from '../../components/QuestionCard.vue'
import { useBillingStore } from '../../stores/billing'
import { useExamStore } from '../../stores/exam'
import { useSubscriptionStore } from '../../stores/subscription'
import { useTargetedStore } from '../../stores/targeted'
import { useUserStore } from '../../stores/user'
import { hasPremiumAccess } from '../../utils/access'
import { mergeTargetPayload } from '../../utils/targetedOptions'
import { YEAR_OPTIONS } from '../../utils/constants'
import { isQuestionScoringSupported, getScoringUnavailableMessage } from '../../utils/questionPresentation'
import { promptLoginForAction, showLoading, toast, hideLoading } from '../../utils/navigation'

const billingStore = useBillingStore()
const subscriptionStore = useSubscriptionStore()
const targetedStore = useTargetedStore()
const examStore = useExamStore()
const userStore = useUserStore()
const selectedCategoryId = ref('')
const selectedRegionId = ref('')
const selectedTargetCode = ref('')
const selectedYears = ref([])
const showYearPicker = ref(false)
const positionTree = computed(() => targetedStore.positionTree || [])
const selectedCategory = computed(() => positionTree.value.find((item) => item.id === selectedCategoryId.value) || positionTree.value[0] || null)
const levelLabels = computed(() => selectedCategory.value?.levelLabels || {})
const regionLevelLabel = computed(() => levelLabels.value.region || '地区 / 来源')
const directionLevelLabel = computed(() => levelLabels.value.direction || '方向')
const currentRegions = computed(() => selectedCategory.value?.children || [])
const selectedRegion = computed(() => currentRegions.value.find((item) => item.id === selectedRegionId.value) || currentRegions.value[0] || null)
const currentDirections = computed(() => selectedRegion.value?.directions || [])
const hasDirectionLevel = computed(() => currentDirections.value.length > 0)
const selectedDirection = computed(() => (
  selectedTargetCode.value
    ? currentDirections.value.find((item) => item.id === selectedTargetCode.value) || null
    : null
))
const categoryNames = computed(() => positionTree.value.map((item) => item.name))
const regionNames = computed(() => currentRegions.value.map((item) => item.name))
const directionNames = computed(() => ['不限', ...currentDirections.value.map((item) => item.name)])
const categoryIndex = computed(() => Math.max(0, positionTree.value.findIndex((item) => item.id === selectedCategoryId.value)))
const regionIndex = computed(() => Math.max(0, currentRegions.value.findIndex((item) => item.id === selectedRegionId.value)))
const directionIndex = computed(() => {
  const index = currentDirections.value.findIndex((item) => item.id === selectedTargetCode.value)
  return index >= 0 ? index + 1 : 0
})
const selectedCategoryName = computed(() => selectedCategory.value?.name || '请选择')
const selectedRegionName = computed(() => selectedRegion.value?.name || '请选择')
const selectedDirectionName = computed(() => selectedDirection.value?.name || '不限')
const activeTarget = computed(() => {
  if (!selectedCategory.value || !selectedRegion.value) return null
  const merged = mergeTargetPayload(selectedCategory.value, selectedRegion.value, selectedDirection.value || {})
  if (selectedYears.value.length) {
    merged.year = selectedYears.value
  }
  return merged
})
const selectedPathLabel = computed(() => [
  selectedCategoryName.value,
  selectedRegionName.value,
  hasDirectionLevel.value && selectedDirection.value ? selectedDirectionName.value : ''
].filter((item) => item && item !== '请选择').join(' / '))
const selectedModeHints = computed(() => {
  const target = activeTarget.value || {}
  const hints = [
    target.interviewFormat ? `形式：${target.interviewFormat}` : '',
    target.questionCount ? `题量：${target.questionCount}题` : '',
    target.timingMode ? `计时：${target.timingMode}` : '',
    target.questionTypeScope ? `题型：${target.questionTypeScope}` : ''
  ].filter(Boolean)
  if (selectedYears.value.length) {
    hints.push(`年份：${selectedYears.value.join('、')}`)
  }
  return hints
})
const yearOptions = computed(() => YEAR_OPTIONS.map((y) => ({ value: y, checked: selectedYears.value.includes(y) })))
const yearLabel = computed(() => selectedYears.value.length ? selectedYears.value.join('、') : '不限年份（可多选）')
const canProceed = computed(() => !!activeTarget.value?.targetCode)
const hasFullAccess = computed(() => hasPremiumAccess(userStore, billingStore, subscriptionStore))
const readonlyMode = computed(() => !hasFullAccess.value)

function findSelectionLocation(targetCode) {
  for (const category of positionTree.value) {
    for (const region of category.children || []) {
      if ((!region.directions?.length) && (region.id === targetCode || region.code === targetCode)) {
        return { category, region, direction: null }
      }
      for (const direction of region.directions || []) {
        if (direction.id === targetCode || direction.code === targetCode) {
          return { category, region, direction }
        }
      }
    }
  }
  return null
}

function applyLocation(location) {
  if (!location) return
  selectedCategoryId.value = location.category.id
  selectedRegionId.value = location.region.id
  selectedTargetCode.value = location.direction?.id || location.direction?.code || ''
}

function selectCategory(category) {
  const region = category?.children?.[0]
  applyLocation(category && region ? { category, region, direction: null } : null)
}

function selectRegion(region) {
  applyLocation(selectedCategory.value && region ? { category: selectedCategory.value, region, direction: null } : null)
}

function selectDirection(direction) {
  selectedTargetCode.value = direction?.id || direction?.code || ''
}

function onCategoryPickerChange(event) {
  selectCategory(positionTree.value[Number(event.detail.value)])
}

function onRegionPickerChange(event) {
  selectRegion(currentRegions.value[Number(event.detail.value)])
}

function onDirectionPickerChange(event) {
  const index = Number(event.detail.value)
  selectDirection(index <= 0 ? null : currentDirections.value[index - 1])
}

function onYearChange(event) {
  selectedYears.value = event.detail.value || []
}

function initializeSelection() {
  const code = targetedStore.selectedTarget?.targetCode
  const location = findSelectionLocation(code) || findSelectionLocation(selectedTargetCode.value)
  if (location) {
    applyLocation(location)
    return
  }
  selectCategory(positionTree.value[0])
}

watch(positionTree, initializeSelection, { immediate: true })

onShow(() => {
  targetedStore.fetchPositionTree().then(initializeSelection).catch(initializeSelection)
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
  if (activeTarget.value) targetedStore.setTarget(activeTarget.value)
}

function buildFocusUrl() {
  const query = Object.entries(activeTarget.value || {})
    .filter(([, value]) => value !== undefined && value !== null && String(value).trim() !== '')
    .map(([key, value]) => `${encodeURIComponent(key)}=${encodeURIComponent(value)}`)
    .join('&')
  return `/pages/targeted/focus${query ? `?${query}` : ''}`
}

function goFocus() {
  if (!canProceed.value) return
  const url = buildFocusUrl()
  if (!promptLoginForAction('分析面试重点', url)) return
  if (readonlyMode.value) {
    toast('请先开通套餐后使用定向备面')
    return
  }
  syncSelection()
  uni.navigateTo({ url })
}

async function generate() {
  if (!canProceed.value) {
    toast('请先选择考试方向')
    return
  }
  if (!promptLoginForAction('生成定向训练题', '/pages/targeted/index')) return
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
      toast('暂无匹配题目，请选择已有真实题库的考试方向')
      return
    }
  } catch (error) {
    toast(error?.message || '生成失败')
  } finally {
    hideLoading()
  }
}

async function startQuestion(question) {
  if (!promptLoginForAction('开始定向练习', '/pages/targeted/index')) return
  if (readonlyMode.value) return
  if (!isQuestionScoringSupported(question)) {
    toast(getScoringUnavailableMessage(1))
    return
  }
  showLoading('创建考场')
  try {
    const prefs = userStore.preferences || {}
    const target = activeTarget.value || {}
    await examStore.startFromQuestions([{
      ...question,
      prepTime: Number(target.prepTime || prefs.defaultPrepTime || question?.prepTime || 90),
      answerTime: Number(target.answerTime || prefs.defaultAnswerTime || question?.answerTime || 180),
      timingMode: target.timingMode || question?.timingMode || '',
      interviewFormat: target.interviewFormat || question?.interviewFormat || ''
    }], 'targeted')
    uni.navigateTo({ url: '/pages/exam/room' })
  } catch (error) {
    toast(error?.message || '无法开始练习')
  } finally {
    hideLoading()
  }
}

function startGeneratedPractice() {
  if (!promptLoginForAction('开始定向练习', '/pages/exam/prepare?source=targeted')) return
  if (readonlyMode.value) return
  uni.navigateTo({ url: '/pages/exam/prepare?source=targeted' })
}

function goPricing() {
  if (!promptLoginForAction('开通套餐', '/pages/pricing/index')) return
  uni.navigateTo({ url: '/pages/pricing/index' })
}

function startTrial() {
  if (!promptLoginForAction('试用 1 题', '/pages/exam/prepare?trial=1')) return
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

.picker-row,
.picker-row__value,
.picker-summary {
  display: block;
}

.picker-card {
  padding-bottom: 18rpx;
}

.picker-row {
  display: flex;
  justify-content: space-between;
  gap: 24rpx;
  padding: 22rpx 0;
  border-bottom: 1rpx solid #eef2f6;
  color: #2a3648;
  font-size: 27rpx;
}

.picker-row--last {
  border-bottom: 0;
}

.picker-row__value {
  max-width: 440rpx;
  color: #1b5faa;
  text-align: right;
}

.picker-summary {
  margin-top: 12rpx;
  color: #6f7c8f;
  font-size: 23rpx;
  line-height: 1.5;
}

.mode-hints {
  display: flex;
  flex-wrap: wrap;
  gap: 10rpx;
  margin-top: 14rpx;
}

.mode-hint {
  display: inline-flex;
  padding: 8rpx 12rpx;
  border-radius: 8rpx;
  background: #eef6ff;
  color: #1b5faa;
  font-size: 22rpx;
  line-height: 1.25;
}

.generated-start {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 28rpx;
  padding: 28rpx 32rpx;
  margin-bottom: 20rpx;
}

.generated-start__title {
  display: block;
  color: #2a3648;
  font-size: 27rpx;
  font-weight: 700;
}

.generated-start__desc {
  display: block;
  margin-top: 8rpx;
  color: #6f7c8f;
  font-size: 24rpx;
}

.year-overlay {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: rgba(0, 0, 0, 0.4);
  z-index: 1000;
  display: flex;
  align-items: flex-end;
  justify-content: center;
}

.year-modal {
  width: 100%;
  max-height: 60vh;
  border-radius: 24rpx 24rpx 0 0;
  overflow-y: auto;
  padding-bottom: env(safe-area-inset-bottom);
}

.year-checkbox {
  display: flex;
  align-items: center;
  gap: 16rpx;
  padding: 22rpx 0;
  border-bottom: 1rpx solid #eef2f6;
  font-size: 27rpx;
  color: #2a3648;
}

.picker-row--year {
  cursor: pointer;
}
</style>
