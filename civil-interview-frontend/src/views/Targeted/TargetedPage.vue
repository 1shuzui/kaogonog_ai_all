<template>
  <div class="targeted-page page-container">
    <h2>定向备面</h2>
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
        @click="generateAndPractice"
      >
        <ThunderboltOutlined /> 生成题目并开始练习
      </a-button>
    </div>

    <!-- 已生成的题目列表 -->
    <div v-if="targetedStore.generatedQuestions.length" class="targeted-section">
      <div class="section-header">
        <h3>已生成题目</h3>
        <a-button type="link" size="small" @click="generateAndPractice">重新生成</a-button>
      </div>
      <div
        v-for="(q, idx) in targetedStore.generatedQuestions"
        :key="q.id"
        class="card question-item"
        @click="startSinglePractice(q)"
      >
        <div class="question-item__idx">{{ idx + 1 }}</div>
        <div class="question-item__content">
          <div class="question-item__stem">{{ q.stem }}</div>
          <a-tag :color="dimensionColor(q.dimension)" size="small">{{ dimensionName(q.dimension) }}</a-tag>
        </div>
        <RightOutlined class="question-item__arrow" />
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed } from 'vue'
import { useRouter } from 'vue-router'
import { SearchOutlined, ThunderboltOutlined, RightOutlined } from '@ant-design/icons-vue'
import { useTargetedStore } from '@/stores/targeted'
import { PROVINCES, POSITION_SYSTEMS, DIMENSIONS } from '@/utils/constants'

const router = useRouter()
const targetedStore = useTargetedStore()

const provinces = PROVINCES
const positionSystems = POSITION_SYSTEMS

const selectedProvince = ref(targetedStore.selectedProvince || '')
const selectedPosition = ref(targetedStore.selectedPosition || '')

const canProceed = computed(() => !!selectedProvince.value && !!selectedPosition.value)

function dimensionName(key) {
  const dim = DIMENSIONS.find(d => d.key === key)
  return dim ? dim.name : key
}

function dimensionColor(key) {
  const colors = { analysis: 'blue', practical: 'green', emergency: 'orange', legal: 'purple', logic: 'cyan', expression: 'geekblue' }
  return colors[key] || 'default'
}

function syncSelection() {
  targetedStore.setSelection(selectedProvince.value, selectedPosition.value)
}

function goToFocusAnalysis() {
  syncSelection()
  router.push('/targeted/focus')
}

async function generateAndPractice() {
  syncSelection()
  await targetedStore.fetchGeneratedQuestions(5)
}

function startSinglePractice(question) {
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

.question-item__arrow {
  color: @text-secondary;
  margin-left: 8px;
  flex-shrink: 0;
}
</style>
