<template>
  <div class="targeted-page page-container">
    <div class="targeted-page__header">
      <a-button type="text" @click="$router.back()">返回</a-button>
      <h2>定向备面</h2>
    </div>
    <p class="targeted-page__desc">选择省份和岗位系统，获取针对性面试重点分析和高概率真题</p>

    <!-- 省份选择 -->
    <div class="card targeted-section">
      <h3>选择省份</h3>
      <div class="selector-grid">
        <div
          v-for="p in provinces"
          :key="p.code"
          class="selector-chip"
          :class="{ active: selectedProvince === p.code }"
          @click="selectedProvince = p.code"
        >
          {{ p.name }}
        </div>
      </div>
    </div>

    <!-- 岗位选择 -->
    <div class="card targeted-section">
      <h3>选择岗位系统</h3>
      <div class="selector-grid">
        <div
          v-for="pos in positionSystems"
          :key="pos.code"
          class="selector-chip"
          :class="{ active: selectedPosition === pos.code }"
          @click="selectedPosition = pos.code"
        >
          {{ pos.name }}
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
        @click="generateAndPractice('local')"
      >
        <ThunderboltOutlined /> 匹配真题并开始练习
      </a-button>
      <a-button
        size="large"
        block
        :disabled="!canProceed"
        :loading="targetedStore.generateLoading"
        @click="generateAndPractice('ai')"
      >
        <ThunderboltOutlined /> AI生成定向题
      </a-button>
    </div>

    <!-- 已生成的题目列表 -->
    <div v-if="targetedStore.generatedQuestions.length" class="targeted-section">
      <div class="section-header">
        <h3>已生成题目</h3>
        <div class="section-header__actions">
          <a-button type="primary" size="small" @click="startBatchPractice">整组随机作答</a-button>
          <a-button type="link" size="small" @click="generateAndPractice(targetedStore.generationMode || 'local')">重新生成</a-button>
        </div>
      </div>
      <a-alert
        v-if="targetedStore.generationMeta"
        class="targeted-summary"
        type="info"
        show-icon
        :message="generationSummary"
      />
      <div
        v-for="(q, idx) in targetedStore.generatedQuestions"
        :key="q.id"
        class="card question-item"
        @click="startSinglePractice(q)"
      >
        <div class="question-item__idx">{{ idx + 1 }}</div>
        <div class="question-item__content">
          <div class="question-item__stem">{{ q.stem }}</div>
          <div class="question-item__meta">
            <a-tag :color="dimensionColor(q.dimension)" size="small">{{ dimensionName(q.dimension) }}</a-tag>
            <a-tag v-if="q.questionSourceLabel" color="green" size="small">{{ q.questionSourceLabel }}</a-tag>
            <a-tag v-if="generationSourceLabel(q)" color="gold" size="small">{{ generationSourceLabel(q) }}</a-tag>
            <a-tag v-if="q.province" color="blue" size="small">{{ provinceName(q.province) }}</a-tag>
          </div>
          <div v-if="q.sourceDocument" class="question-item__source">
            {{ q.sourceDocument }}
          </div>
        </div>
        <RightOutlined class="question-item__arrow" />
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { SearchOutlined, ThunderboltOutlined, RightOutlined } from '@ant-design/icons-vue'
import { Modal } from 'ant-design-vue'
import { useTargetedStore } from '@/stores/targeted'
import { getPositions } from '@/api/targeted'
import { PROVINCES, POSITION_SYSTEMS, DIMENSIONS } from '@/utils/constants'

const router = useRouter()
const targetedStore = useTargetedStore()

const provinces = PROVINCES
const positionSystems = ref(POSITION_SYSTEMS)

const selectedProvince = ref(targetedStore.selectedProvince || '')
const selectedPosition = ref(targetedStore.selectedPosition || '')

const canProceed = computed(() => !!selectedProvince.value && !!selectedPosition.value)
const generationSummary = computed(() => {
  const meta = targetedStore.generationMeta
  if (!meta) return ''
  const parts = []
  parts.push(meta.requestedMode === 'ai' ? '当前列表来源：AI定向生成' : '当前列表来源：本地真题/题库匹配')
  if (meta.localBankCount) {
    parts.push(`本地真题/题库题 ${meta.localBankCount} 道`)
  }
  if (meta.aiCount) {
    parts.push(`AI生成 ${meta.aiCount} 道`)
  }
  if (meta.fallbackCount) {
    parts.push(`补足回退 ${meta.fallbackCount} 道`)
  }
  return parts.join('，') || `共 ${meta.total} 道题`
})

function dimensionName(key) {
  const dim = DIMENSIONS.find(d => d.key === key)
  return dim ? dim.name : key
}

function dimensionColor(key) {
  const colors = { analysis: 'blue', practical: 'green', emergency: 'orange', legal: 'purple', logic: 'cyan', expression: 'geekblue' }
  return colors[key] || 'default'
}

function provinceName(code) {
  const province = PROVINCES.find(item => item.code === code)
  return province ? province.name : code
}

function generationSourceLabel(question) {
  const mapping = {
    local_bank: '本地题库',
    llm: 'AI补充',
    fallback_bank: '题库补足'
  }
  return mapping[question?.generationSource] || ''
}

function syncSelection() {
  targetedStore.setSelection(selectedProvince.value, selectedPosition.value)
}

function goToFocusAnalysis() {
  syncSelection()
  router.push('/targeted/focus')
}

async function generateAndPractice(sourceMode = 'local') {
  syncSelection()
  const questions = await targetedStore.fetchGeneratedQuestions(5, { sourceMode })
  const meta = targetedStore.generationMeta
  if (!questions?.length || !meta) return

  if (sourceMode === 'ai' && meta.aiCount > 0) {
    Modal.info({
      title: '已生成 AI 定向题',
      content: `本次共生成 ${meta.total} 道题，其中 AI 生成 ${meta.aiCount} 道。`
    })
    return
  }

  if (meta.fallbackCount > 0) {
    Modal.warning({
      title: 'AI 定向题不可用，已回退到本地题库',
      content: meta.fallbackReason || `本次共生成 ${meta.total} 道题，当前以本地真题/题库题为主。`
    })
    return
  }

  if (meta.localBankCount > 0 && meta.aiCount === 0) {
    Modal.info({
      title: '已从本地题库生成练习题',
      content: meta.fallbackReason || `本次共生成 ${meta.total} 道题，当前以本地真题/题库题为主。`
    })
  }
}

function startSinglePractice(question) {
  sessionStorage.setItem('targeted_question', JSON.stringify(question))
  router.push({ path: '/exam/prepare', query: { questionId: question.id, source: 'targeted' } })
}

function startBatchPractice() {
  if (!targetedStore.generatedQuestions.length) {
    return
  }
  sessionStorage.setItem('targeted_question_batch', JSON.stringify(targetedStore.generatedQuestions))
  router.push({ path: '/exam/prepare', query: { source: 'targeted' } })
}

onMounted(async () => {
  try {
    const positions = await getPositions()
    if (positions.length) {
      positionSystems.value = positions
    }
  } catch {
    positionSystems.value = POSITION_SYSTEMS
  }
})
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

.targeted-page__header {
  display: flex;
  align-items: center;
  gap: 8px;
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

.selector-grid {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.selector-chip {
  padding: 8px 16px;
  border-radius: 20px;
  border: 1px solid @border-color;
  font-size: @font-size-sm;
  color: @text-regular;
  cursor: pointer;
  transition: all 0.2s;
  background: @card-bg;

  &:hover {
    border-color: @primary-color;
    color: @primary-color;
  }

  &.active {
    background: @primary-color;
    color: #fff;
    border-color: @primary-color;
  }
}

.targeted-actions {
  display: flex;
  flex-direction: column;
  gap: 10px;
  margin-bottom: 16px;
}

.section-header__actions {
  display: flex;
  align-items: center;
  gap: 8px;
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

.targeted-summary {
  margin-bottom: 12px;
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
  font-size: @font-size-base;
  color: @text-regular;
  margin-bottom: 6px;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
}

.question-item__meta {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
}

.question-item__source {
  margin-top: 8px;
  font-size: @font-size-xs;
  color: @text-secondary;
}

.question-item__arrow {
  color: @text-secondary;
  margin-left: 8px;
  flex-shrink: 0;
}
</style>
