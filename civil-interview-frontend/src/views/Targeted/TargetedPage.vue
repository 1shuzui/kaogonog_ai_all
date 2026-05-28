<template>
  <div class="targeted-page page-container">
    <h2>定向备面</h2>
    <p class="targeted-page__desc">按真实考试体系、地区来源和岗位方向选择，分析对应题库重点。</p>

    <div class="card targeted-picker">
      <div class="targeted-picker__row">
        <label>考试体系</label>
        <a-select
          v-model:value="selectedCategoryId"
          class="targeted-picker__select"
          placeholder="请选择考试体系"
          @change="handleCategoryChange"
        >
          <a-select-option v-for="category in positionTree" :key="category.id" :value="category.id">
            {{ category.name }}
          </a-select-option>
        </a-select>
      </div>

      <div class="targeted-picker__row">
        <label>{{ regionLevelLabel }}</label>
        <a-select
          v-model:value="selectedRegionId"
          class="targeted-picker__select"
          placeholder="请选择地区或来源"
          :disabled="!currentRegions.length"
          @change="handleRegionChange"
        >
          <a-select-option v-for="region in currentRegions" :key="region.id" :value="region.id">
            {{ region.name }}
          </a-select-option>
        </a-select>
      </div>

      <div v-if="hasDirectionLevel" class="targeted-picker__row">
        <label>{{ directionLevelLabel }}</label>
        <a-select
          v-model:value="selectedTargetCode"
          class="targeted-picker__select"
          placeholder="请选择练习方向"
          :disabled="!currentDirections.length"
          @change="handleDirectionChange"
        >
          <a-select-option v-for="direction in currentDirections" :key="direction.id" :value="direction.id">
            {{ direction.name }}
          </a-select-option>
        </a-select>
      </div>

      <div v-if="activeTarget" class="targeted-picker__summary">
        当前选择：{{ selectedPathLabel }}
        <div v-if="selectedModeHints.length" class="targeted-picker__meta">
          <span v-for="hint in selectedModeHints" :key="hint">{{ hint }}</span>
        </div>
      </div>
    </div>

    <!-- 操作按钮 -->
    <div class="targeted-actions">
      <a-button
        type="primary"
        size="large"
        block
        :disabled="!canProceed"
        @click="goToFocusAnalysis"
      >
        <SearchOutlined /> 分析面试重点
      </a-button>
      <a-button
        size="large"
        block
        :disabled="!canProceed"
        :loading="targetedStore.generateLoading"
        @click="generateTargetedQuestions"
      >
        <ThunderboltOutlined /> 生成练习题目
      </a-button>
    </div>

    <!-- 已生成的题目列表 -->
    <div v-if="targetedStore.generatedQuestions.length" class="targeted-section">
      <div class="section-header">
        <h3>已生成题目</h3>
        <a-button type="link" size="small" @click="generateTargetedQuestions">重新生成</a-button>
      </div>
      <div class="generated-start card">
        <div>
          <strong>已为当前考试方向准备 {{ targetedStore.generatedQuestions.length }} 道练习题</strong>
          <p>先核对题目，再进入专项练习。</p>
        </div>
        <a-button type="primary" size="large" @click="startGeneratedPractice">
          <PlayCircleOutlined /> 开始练习
        </a-button>
      </div>
      <div
        v-for="(q, idx) in targetedStore.generatedQuestions"
        :key="q.id"
        class="card question-item"
        @click="startSinglePractice(q)"
      >
        <div class="question-item__idx">{{ idx + 1 }}</div>
        <div class="question-item__content">
          <QuestionMetaTags :question="q" emphasis compact :max-keywords="4" />
          <div class="question-item__stem">
            <QuestionRichContent :text="q.stem" compact :collapsed-height="112" />
          </div>
        </div>
        <RightOutlined class="question-item__arrow" />
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, watch } from 'vue'
import { useRouter } from 'vue-router'
import { SearchOutlined, ThunderboltOutlined, RightOutlined, PlayCircleOutlined } from '@ant-design/icons-vue'
import { message } from 'ant-design-vue'
import { useTargetedStore } from '@/stores/targeted'
import { useUserStore } from '@/stores/user'
import { useBillingStore } from '@/stores/billing'
import { hasPremiumAccess } from '@/utils/access'
import { mergeTargetPayload } from '@/utils/targetedOptions'
import QuestionMetaTags from '@/components/common/QuestionMetaTags.vue'
import QuestionRichContent from '@/components/common/QuestionRichContent.vue'
import { getScoringUnavailableMessage, isQuestionScoringSupported } from '@/utils/scoringSupport'

const router = useRouter()
const targetedStore = useTargetedStore()
const userStore = useUserStore()
const billingStore = useBillingStore()

const selectedCategoryId = ref('')
const selectedRegionId = ref('')
const selectedTargetCode = ref('')
const hasFullAccess = computed(() => hasPremiumAccess(userStore, billingStore))
const positionTree = computed(() => targetedStore.positionTree || [])
const selectedCategory = computed(() => positionTree.value.find((item) => item.id === selectedCategoryId.value) || positionTree.value[0] || null)
const levelLabels = computed(() => selectedCategory.value?.levelLabels || {})
const regionLevelLabel = computed(() => levelLabels.value.region || '地区 / 来源')
const directionLevelLabel = computed(() => levelLabels.value.direction || '方向')
const currentRegions = computed(() => selectedCategory.value?.children || [])
const selectedRegion = computed(() => currentRegions.value.find((item) => item.id === selectedRegionId.value) || currentRegions.value[0] || null)
const currentDirections = computed(() => selectedRegion.value?.directions || [])
const hasDirectionLevel = computed(() => currentDirections.value.length > 0)
const selectedDirection = computed(() => currentDirections.value.find((item) => item.id === selectedTargetCode.value) || currentDirections.value[0] || null)
const activeTarget = computed(() => (
  selectedCategory.value && selectedRegion.value && (!hasDirectionLevel.value || selectedDirection.value)
    ? mergeTargetPayload(selectedCategory.value, selectedRegion.value, selectedDirection.value || {})
    : null
))
const selectedPathLabel = computed(() => [
  selectedCategory.value?.name,
  selectedRegion.value?.name,
  hasDirectionLevel.value ? selectedDirection.value?.name : ''
].filter(Boolean).join(' / '))
const selectedModeHints = computed(() => {
  const target = activeTarget.value || {}
  return [
    target.interviewFormat ? `形式：${target.interviewFormat}` : '',
    target.questionCount ? `题量：${target.questionCount}题` : '',
    target.timingMode ? `计时：${target.timingMode}` : '',
    target.questionTypeScope ? `题型：${target.questionTypeScope}` : ''
  ].filter(Boolean)
})
const canProceed = computed(() => !!activeTarget.value?.targetCode)

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
  const direction = region?.directions?.[0]
  applyLocation(category && region ? { category, region, direction: direction || null } : null)
}

function selectRegion(region) {
  const direction = region?.directions?.[0]
  applyLocation(selectedCategory.value && region ? { category: selectedCategory.value, region, direction: direction || null } : null)
}

function selectDirection(direction) {
  if (!direction) return
  selectedTargetCode.value = direction.id || direction.code
}

function handleCategoryChange(categoryId) {
  selectCategory(positionTree.value.find((item) => item.id === categoryId))
}

function handleRegionChange(regionId) {
  selectRegion(currentRegions.value.find((item) => item.id === regionId))
}

function handleDirectionChange(directionId) {
  selectDirection(currentDirections.value.find((item) => item.id === directionId))
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

onMounted(async () => {
  await targetedStore.fetchPositionTree()
  initializeSelection()
})

function syncSelection() {
  if (activeTarget.value) targetedStore.setTarget(activeTarget.value)
}

function routeQueryFromTarget(target) {
  return Object.fromEntries(
    Object.entries(target || {}).filter(([, value]) => value !== undefined && value !== null && String(value).trim() !== '')
  )
}

async function ensureFullAccess() {
  await userStore.loadUserInfo().catch(() => null)
  if (hasFullAccess.value) return true
  billingStore.openPaywall('/targeted', '定向备考')
  router.push('/')
  return false
}

async function goToFocusAnalysis() {
  if (!(await ensureFullAccess())) return
  syncSelection()
  router.push({
    path: '/targeted/focus',
    query: routeQueryFromTarget(activeTarget.value)
  })
}

async function generateTargetedQuestions() {
  if (!(await ensureFullAccess())) return
  syncSelection()
  const questions = await targetedStore.fetchGeneratedQuestions(5)
  if (!questions?.length) {
    message.warning('题库中暂无匹配题目，请选择已有真实题库的考试方向。')
    return
  }
  message.success('题目已生成，请在下方核对后开始练习。')
}

function startGeneratedPractice() {
  if (!targetedStore.generatedQuestions.length) {
    message.warning('请先生成练习题目。')
    return
  }
  router.push({ path: '/exam/prepare', query: { source: 'targeted' } })
}

function startSinglePractice(question) {
  if (!isQuestionScoringSupported(question)) {
    message.warning(getScoringUnavailableMessage(1))
    return
  }

  sessionStorage.setItem('targeted_question', JSON.stringify(question))
  router.push({ path: '/exam/prepare', query: { questionId: question.id, source: 'targeted' } })
}
</script>

<style lang="less" scoped>
@import '@/styles/variables.less';

.targeted-page {
  h2 {
    font-size: @font-size-xl;
    color: @text-primary;
    margin-bottom: 4px;
  }
}

.targeted-page__desc {
  font-size: @font-size-sm;
  color: @text-secondary;
  margin-bottom: 16px;
}

.targeted-section {
  padding: 16px;
  margin-bottom: 12px;

  h3 {
    font-size: @font-size-lg;
    color: @text-primary;
    margin-bottom: 12px;
  }
}

.targeted-picker {
  display: grid;
  gap: 12px;
  padding: 16px;
  margin-bottom: 16px;
}

.targeted-picker__row {
  display: grid;
  grid-template-columns: 112px minmax(0, 1fr);
  gap: 12px;
  align-items: center;

  label {
    color: @text-secondary;
    font-size: @font-size-sm;
    font-weight: 600;
  }
}

.targeted-picker__select {
  width: 100%;
}

.targeted-picker__summary {
  padding-top: 10px;
  border-top: 1px solid @divider-color;
  color: @text-secondary;
  font-size: @font-size-sm;
}

.targeted-picker__meta {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  margin-top: 8px;

  span {
    padding: 4px 8px;
    border-radius: 6px;
    background: @bg-light-blue;
    color: @primary-color;
    font-size: @font-size-xs;
  }
}

.targeted-actions {
  display: flex;
  flex-direction: column;
  gap: 10px;
  margin-bottom: 16px;
}

.section-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 10px;

  h3 {
    font-size: @font-size-lg;
    color: @text-primary;
    margin: 0;
  }
}

.generated-start {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 14px;
  padding: 14px 16px;
  margin-bottom: 10px;

  strong {
    display: block;
    color: @text-primary;
    font-size: @font-size-base;
  }

  p {
    margin: 4px 0 0;
    color: @text-secondary;
    font-size: @font-size-sm;
  }
}

.question-item {
  display: flex;
  align-items: center;
  padding: 14px 16px;
  margin-bottom: 8px;
  cursor: pointer;
  transition: box-shadow 0.2s;

  &:hover {
    box-shadow: @shadow-popup;
  }
}

@media (max-width: 768px) {
  .targeted-picker__row {
    grid-template-columns: 1fr;
    gap: 6px;
  }

  .generated-start {
    align-items: stretch;
    flex-direction: column;
  }
}

.question-item__idx {
  width: 28px;
  height: 28px;
  border-radius: 50%;
  background: @bg-light-blue;
  color: @primary-color;
  font-weight: 600;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
  margin-right: 12px;
  font-size: @font-size-sm;
}

.question-item__content {
  flex: 1;
  min-width: 0;
}

.question-item__stem {
  margin-top: 8px;
}

.question-item__stem :deep(.question-rich-content__body) {
  color: @text-regular;
}

.question-item__arrow {
  color: @text-secondary;
  margin-left: 8px;
  flex-shrink: 0;
}
</style>
