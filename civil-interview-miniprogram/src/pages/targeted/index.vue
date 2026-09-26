<!--
小程序定向备面页，负责按考试体系、地区/来源和岗位方向选择目标，并进入重点分析或生成训练题。

本页允许未登录浏览分类树，方向可以选“不限”；但点击分析、生成、试用或开通前必须走登录/权益拦截。
选择器标题由考试体系的 `levelLabels` 决定，例如法检使用“岗位方向 -> 地区/来源”，不能影响其他考试体系的层级名称。

@param: 无；分类来自后端 positions 接口或 targetedOptions 兜底树，用户选择保存在页面状态中。
@return: 渲染上下式分类选择、空态说明、试用/开通入口和训练入口。
@raises: 不主动抛业务异常；接口失败、未登录和权益不足由请求层、登录拦截或页面空态承接。
-->
<template>
  <view class="motion-page page page--tab" :class="motionClass" :style="motionStyle">
    <view class="motion-page-heading"><view><text class="motion-eyebrow">选好方向 · 贴近岗位</text><text class="page-title">定向备面</text></view><view class="motion-heading-icon"><LearnerIcon name="environment" :size="32" /></view></view>
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
      <LightSelector class="targeted-category-selector" title="考试体系" :options="categoryNames" :value="categoryIndex" @change="onCategoryPickerChange">
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
      <button class="primary-button analysis-submit" :disabled="targetedStore.focusLoading" @tap="goFocus">{{ targetedStore.focusLoading ? '正在分析…' : '分析面试重点' }}</button>
      <button class="secondary-button" :disabled="!canProceed" :loading="targetedStore.generateLoading" @tap="generate">
        生成题目
      </button>
    </view>

    <text v-if="selectionError" class="selection-error">{{ selectionError }}</text>
    <FocusAnalysisCard class="targeted-analysis" :status="targetedStore.focusStatus" :data="targetedStore.focusData" :error="targetedStore.focusError" :slow="targetedStore.focusSlow" :target-label="analysisTargetLabel" @retry="goFocus" @cancel="targetedStore.cancelFocusAnalysis()" />

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

    <LearnerSheet class="targeted-year-sheet" :show="showYearPicker" title="选择年份" :body-height="yearOptions.length * 52 + 110" @close="showYearPicker = false">
        <text class="ui-helper">{{ !hasFullAccess ? '开通题库后可查看已收录年份。' : filterMetadata.loading.value ? '正在读取题库年份…' : '以下为全题库已收录年份，所选方向是否有题以实际分析结果为准。' }}</text>
        <view v-if="filterMetadata.error.value"><text class="ui-error">{{ filterMetadata.error.value }}</text><button class="ui-link" @tap="refreshFilterMetadata">重新加载</button></view>
        <text v-else-if="hasFullAccess && !filterMetadata.loading.value && !yearOptions.length" class="ui-helper">题库暂无可选年份，可继续使用不限年份。</text>
        <button v-if="selectedYears.length" class="ui-link" @tap="selectedYears = []">清除年份条件</button>
        <checkbox-group @change="onYearChange">
          <label v-for="opt in yearOptions" :key="opt.value" class="year-checkbox">
            <checkbox :value="opt.value" :checked="opt.checked" />
            <text>{{ opt.value }}</text>
          </label>
        </checkbox-group>
    </LearnerSheet>
  </view>
</template>

<script setup>
import LearnerIcon from '../../components/LearnerIcon.vue'
import { usePageMotion } from '../../motion/useMotion'
const { motionClass, motionStyle } = usePageMotion()
import { computed, ref, watch } from 'vue'
import { onShow, onHide, onUnload } from '@dcloudio/uni-app'
import FocusAnalysisCard from '../../components/FocusAnalysisCard.vue'
import LightSelector from '../../components/LightSelector.vue'
import LearnerSheet from '../../components/LearnerSheet.vue'
import QuestionCard from '../../components/QuestionCard.vue'
import { useBillingStore } from '../../stores/billing'
import { useExamStore } from '../../stores/exam'
import { useSubscriptionStore } from '../../stores/subscription'
import { useTargetedStore } from '../../stores/targeted'
import { useUserStore } from '../../stores/user'
import { hasPremiumAccess } from '../../utils/access'
import { buildTargetFocusUrl, mergeTargetPayload } from '../../utils/targetedOptions'
import { useQuestionFilters } from '../../utils/useQuestionFilters'
import { miniPracticeUrl } from '../../../../shared/practiceSelection.mjs'
import { isQuestionScoringSupported, getScoringUnavailableMessage } from '../../utils/questionPresentation'
import { promptLoginForAction, showLoading, toast, hideLoading } from '../../utils/navigation'

const billingStore = useBillingStore()
const subscriptionStore = useSubscriptionStore()
const targetedStore = useTargetedStore()
const examStore = useExamStore()
const userStore = useUserStore()
const filterMetadata = useQuestionFilters()
const selectedCategoryId = ref('')
const selectedRegionId = ref('')
const selectedTargetCode = ref('')
const selectedYears = ref([])
const showYearPicker = ref(false)
const selectionError = ref('')
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
const yearOptions = computed(() => filterMetadata.options.value.year.map((y) => ({ value: y, checked: selectedYears.value.includes(y) })))
const yearLabel = computed(() => selectedYears.value.length ? selectedYears.value.join('、') : '不限年份（可多选）')
const canProceed = computed(() => !!activeTarget.value?.targetCode)
const hasFullAccess = computed(() => hasPremiumAccess(userStore, billingStore, subscriptionStore))
const readonlyMode = computed(() => !hasFullAccess.value)
function refreshFilterMetadata() { return filterMetadata.refresh({}, hasFullAccess.value && userStore.isAuthenticated) }
watch(() => hasFullAccess.value && userStore.isAuthenticated, refreshFilterMetadata, { immediate: true })
const analysisTargetLabel = computed(() => {
  const payload = targetedStore.focusParams || {}
  return [payload.examCategory, payload.examSubcategory, payload.targetName, payload.year?.length ? String(payload.year) : ''].filter(Boolean).join(' / ')
})
watch(activeTarget, target => {
  selectionError.value = ''
  if (target) targetedStore.setTarget(target)
}, { deep: true })

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
  const existing = positionTree.value.find(item => item.id === selectedCategoryId.value)
  if (existing?.children?.some(item => item.id === selectedRegionId.value)) return
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
  if (!targetedStore.positionsLoaded) targetedStore.fetchPositionTree().then(initializeSelection).catch(initializeSelection)
  refreshAccessState().catch(() => null)
})
onHide(() => { showYearPicker.value = false; targetedStore.cancelFocusAnalysis() })
onUnload(() => targetedStore.cancelFocusAnalysis())

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
  return buildTargetFocusUrl(activeTarget.value || {})
}

function goFocus() {
  if (targetedStore.focusLoading) return
  selectionError.value = ''
  if (!canProceed.value) { selectionError.value = '请先选择考试体系与地区 / 来源'; return }
  const url = buildFocusUrl()
  if (!promptLoginForAction('分析面试重点', url)) return
  if (readonlyMode.value) {
    toast('请先开通套餐后使用定向备面')
    return
  }
  syncSelection()
  targetedStore.fetchFocusAnalysis().catch(() => null) // visible error state belongs to the task/card
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
  try {
    const questions = await targetedStore.fetchGeneratedQuestions(5)
    if (!questions.length) {
      toast('暂无匹配题目，请选择已有真实题库的考试方向')
      return
    }
  } catch (error) {
    toast(error?.message || '生成失败')
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
  if (!targetedStore.generatedQuestions.length) return toast('请先生成练习题目')
  uni.navigateTo({ url: miniPracticeUrl({ source: 'targeted', questionIds: targetedStore.generatedQuestions.map(question => question.id), filters: targetedStore.selectionPayload }) })
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
.selection-error { display:block; margin:-12px 0 16px; color:#a94438; font-size:25rpx; }
.access-card {
  border-color: #bfd7ef;
  background: #f4f9fe;
}

.access-card__desc {
  display: block;
  color: var(--ui-muted);
  font-size: 14px;
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
  color: var(--ui-text);
  font-size: 14px;
  transition: transform 160ms ease, background-color 160ms ease;
}

.picker-row:active {
  background: #f8fbff;
  transform: translateX(3rpx);
}

.picker-row--last {
  border-bottom: 0;
}

.picker-row__value {
  max-width: 440rpx;
  color: var(--ui-link);
  text-align: right;
}

.picker-summary {
  margin-top: 12rpx;
  color: var(--ui-muted);
  font-size: 14px;
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
  background: var(--ui-soft);
  color: var(--ui-link);
  font-size: 14px;
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
  color: var(--ui-text);
  font-size: 14px;
  font-weight: 700;
}

.generated-start__desc {
  display: block;
  margin-top: 8rpx;
  color: var(--ui-muted);
  font-size: 14px;
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
  animation: year-mask-in 180ms ease-out both;
}

.year-modal {
  width: 100%;
  max-height: 60vh;
  border-radius: 24rpx 24rpx 0 0;
  overflow-y: auto;
  padding-bottom: env(safe-area-inset-bottom);
  animation: year-sheet-up 220ms ease-out both;
}

.year-checkbox {
  display: flex;
  align-items: center;
  gap: 16rpx;
  padding: 22rpx 0;
  border-bottom: 1rpx solid #eef2f6;
  font-size: 14px;
  color: var(--ui-text);
}

.picker-row--year {
  cursor: pointer;
}

@keyframes year-mask-in {
  from {
    opacity: 0;
  }
  to {
    opacity: 1;
  }
}

@keyframes year-sheet-up {
  from {
    opacity: 0;
    transform: translate3d(0, 36rpx, 0);
  }
  to {
    opacity: 1;
    transform: translate3d(0, 0, 0);
  }
}
</style>
