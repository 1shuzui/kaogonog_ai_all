<template>
  <div class="focus-page page-container">
    <div class="focus-header">
      <a-button type="text" @click="$router.back()">
        <LeftOutlined /> 返回
      </a-button>
      <h2>面试重点分析</h2>
    </div>

    <div class="focus-selection card">
      <span class="focus-tag">{{ provinceName }}</span>
      <span class="focus-tag">{{ positionName }}</span>
    </div>

    <a-spin :spinning="targetedStore.focusLoading || localBankLoading" tip="AI正在分析面试重点...">
      <template v-if="normalizedFocusData">
        <!-- 核心考察能力 -->
        <div class="card focus-section">
          <h3><AimOutlined /> 核心考察能力</h3>
          <div v-for="item in normalizedFocusData.coreFocus" :key="item.name" class="focus-ability">
            <div class="focus-ability__header">
              <span class="focus-ability__name">{{ item.name }}</span>
              <span class="focus-ability__weight">{{ item.weight }}%</span>
            </div>
            <a-progress :percent="item.weight" :show-info="false" :stroke-color="primaryColor" size="small" />
            <p class="focus-ability__desc">{{ item.desc }}</p>
          </div>
        </div>

        <!-- 高频题型 -->
        <div class="card focus-section">
          <h3><BarChartOutlined /> 高频题型</h3>
          <div v-for="item in normalizedFocusData.highFreqTypes" :key="item.type" class="freq-type">
            <div class="freq-type__header">
              <span class="freq-type__name">{{ item.type }}</span>
              <a-tag :color="freqColor(item.frequency)">{{ item.frequency }}频</a-tag>
            </div>
            <p class="freq-type__example">{{ item.example }}</p>
          </div>
        </div>

        <!-- 热门话题 -->
        <div class="card focus-section">
          <h3><FireOutlined /> 热门话题</h3>
          <div class="hot-topics">
            <a-tag v-for="topic in normalizedFocusData.hotTopics" :key="topic" color="orange">{{ topic }}</a-tag>
          </div>
        </div>

        <!-- 备考策略 -->
        <div class="card focus-section">
          <h3><BulbOutlined /> 备考策略</h3>
          <div v-for="(s, idx) in normalizedFocusData.strategy" :key="idx" class="strategy-item">
            <div class="strategy-item__num">{{ idx + 1 }}</div>
            <span>{{ s }}</span>
          </div>
        </div>

        <div class="card focus-section" v-if="localBankQuestions.length">
          <div class="focus-local-header">
            <h3><DatabaseOutlined /> 本地题库匹配题</h3>
            <a-button type="primary" size="small" @click="startLocalBatchPractice">整组随机作答</a-button>
          </div>
          <a-alert
            class="focus-local-alert"
            type="info"
            show-icon
            :message="`已从本地题库匹配到 ${localBankQuestions.length} 道 ${provinceName}/${positionName} 相关题目。`"
          />
          <div
            v-for="(question, idx) in localBankQuestions"
            :key="question.id"
            class="local-question-item"
            @click="startLocalSinglePractice(question)"
          >
            <div class="local-question-item__idx">{{ idx + 1 }}</div>
            <div class="local-question-item__content">
              <div class="local-question-item__stem">{{ question.stem }}</div>
              <div class="local-question-item__meta">
                <a-tag color="blue">{{ dimensionName(question.dimension) }}</a-tag>
                <a-tag v-if="question.questionSourceLabel" color="green">{{ question.questionSourceLabel }}</a-tag>
                <a-tag v-if="question.sourceDocument" color="gold">{{ question.sourceDocument }}</a-tag>
              </div>
            </div>
            <RightOutlined class="local-question-item__arrow" />
          </div>
        </div>

        <!-- 开始练习 -->
        <div class="focus-actions">
          <a-button
            type="primary"
            size="large"
            block
            :loading="targetedStore.generateLoading"
            @click="startTargetedPractice"
          >
            <ThunderboltOutlined /> AI生成针对性题目并开始练习
          </a-button>
        </div>
      </template>

      <EmptyState v-else-if="!targetedStore.focusLoading" text="暂无分析数据，请返回选择省份和岗位" />
    </a-spin>
  </div>
</template>

<script setup>
import { computed, onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { LeftOutlined, AimOutlined, BarChartOutlined, FireOutlined, BulbOutlined, ThunderboltOutlined, DatabaseOutlined, RightOutlined } from '@ant-design/icons-vue'
import { message } from 'ant-design-vue'
import { useTargetedStore } from '@/stores/targeted'
import { getPositions, generateQuestions } from '@/api/targeted'
import { PROVINCES, POSITION_SYSTEMS, DIMENSIONS } from '@/utils/constants'
import EmptyState from '@/components/common/EmptyState.vue'

const router = useRouter()
const targetedStore = useTargetedStore()
const primaryColor = '#1B5FAA'
const positionSystems = ref(POSITION_SYSTEMS)
const localBankQuestions = ref([])
const localBankLoading = ref(false)

const focusData = computed(() => targetedStore.focusData)
const normalizedFocusData = computed(() => {
  const raw = focusData.value
  if (!raw) return null
  if (Array.isArray(raw.coreFocus)) {
    return raw
  }

  const focusAreas = Array.isArray(raw.focusAreas) ? raw.focusAreas : []
  const priorityWeight = { high: 88, medium: 72, low: 58 }
  const priorityLabel = { high: '高', medium: '中', low: '低' }
  return {
    coreFocus: focusAreas.map((item) => ({
      name: item.label || dimensionName(item.type),
      weight: priorityWeight[item.priority] || 65,
      desc: item.description || ''
    })),
    highFreqTypes: focusAreas.map((item) => ({
      type: dimensionName(item.type),
      frequency: priorityLabel[item.priority] || '中',
      example: item.description || `${positionName.value}岗位会重点考察 ${dimensionName(item.type)}。`
    })),
    hotTopics: focusAreas.map((item) => item.label).filter(Boolean),
    strategy: [
      `先用本地题库中与 ${provinceName.value}/${positionName.value} 相关的题目热身，熟悉题感和表述风格。`,
      `答题时优先体现岗位职责、政策依据、群众沟通和流程执行，避免空泛套话。`,
      `完成本地题库练习后，再进入 AI 定向题做强化，检查自己是否能迁移到新场景。`
    ]
  }
})

const provinceName = computed(() => {
  const p = PROVINCES.find(p => p.code === targetedStore.selectedProvince)
  return p ? p.name : targetedStore.selectedProvince
})

const positionName = computed(() => {
  const p = positionSystems.value.find(p => p.code === targetedStore.selectedPosition)
  return p ? p.name : targetedStore.selectedPosition
})

function freqColor(freq) {
  if (freq === '高') return 'red'
  if (freq === '中') return 'orange'
  return 'default'
}

function dimensionName(key) {
  const dim = DIMENSIONS.find(item => item.key === key)
  return dim ? dim.name : (key || '综合分析')
}

async function loadLocalQuestionBank() {
  if (!targetedStore.hasSelection) return
  localBankLoading.value = true
  try {
    const result = await generateQuestions({
      province: targetedStore.selectedProvince,
      position: targetedStore.selectedPosition,
      count: 5
    }, 'local')
    localBankQuestions.value = result?.questions || []
  } finally {
    localBankLoading.value = false
  }
}

onMounted(() => {
  if (!targetedStore.hasSelection) {
    router.replace('/targeted')
    return
  }
  if (!targetedStore.focusData) {
    void targetedStore.fetchFocusAnalysis()
  }
  void loadLocalQuestionBank()
  void (async () => {
    try {
      const positions = await getPositions()
      if (positions.length) {
        positionSystems.value = positions
      }
    } catch {
      positionSystems.value = POSITION_SYSTEMS
    }
  })()
})

async function startTargetedPractice() {
  const questions = await targetedStore.fetchGeneratedQuestions(5, { sourceMode: 'ai' })
  if (questions?.[0]?.generationSource === 'fallback_bank') {
    message.warning(questions[0].generationFallbackReason || 'AI 出题不可用，已回退为题库随机题')
  } else if (questions?.length) {
    message.success(`已生成 ${questions.length} 道针对性题目，开始练习`)
  }
  if (targetedStore.generatedQuestions.length) {
    router.push({ path: '/exam/prepare', query: { source: 'targeted' } })
  }
}

function startLocalSinglePractice(question) {
  sessionStorage.setItem('targeted_question', JSON.stringify(question))
  router.push({ path: '/exam/prepare', query: { questionId: question.id, source: 'targeted' } })
}

function startLocalBatchPractice() {
  if (!localBankQuestions.value.length) return
  sessionStorage.setItem('targeted_question_batch', JSON.stringify(localBankQuestions.value))
  router.push({ path: '/exam/prepare', query: { source: 'targeted' } })
}
</script>

<style lang="less" scoped>
@import '@/styles/variables.less';

.focus-header {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 16px;

  h2 {
    font-size: @font-size-xl;
    color: @text-primary;
    margin: 0;
  }
}

.focus-selection {
  display: flex;
  gap: 8px;
  padding: 12px 16px;
  margin-bottom: 16px;
}

.focus-tag {
  padding: 4px 12px;
  border-radius: 16px;
  background: @bg-light-blue;
  color: @primary-color;
  font-size: @font-size-sm;
  font-weight: 500;
}

.focus-section {
  padding: 16px;
  margin-bottom: 12px;

  h3 {
    font-size: @font-size-lg;
    color: @text-primary;
    margin-bottom: 14px;
    display: flex;
    align-items: center;
    gap: 6px;
  }
}

.focus-ability {
  margin-bottom: 14px;

  &:last-child {
    margin-bottom: 0;
  }
}

.focus-ability__header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 4px;
}

.focus-ability__name {
  font-size: @font-size-base;
  color: @text-regular;
  font-weight: 500;
}

.focus-ability__weight {
  font-size: @font-size-sm;
  color: @primary-color;
  font-weight: 600;
}

.focus-ability__desc {
  font-size: @font-size-xs;
  color: @text-secondary;
  margin-top: 4px;
  margin-bottom: 0;
}

.freq-type {
  margin-bottom: 14px;
  padding-bottom: 14px;
  border-bottom: 1px solid @divider-color;

  &:last-child {
    margin-bottom: 0;
    padding-bottom: 0;
    border-bottom: none;
  }
}

.freq-type__header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 6px;
}

.freq-type__name {
  font-size: @font-size-base;
  color: @text-regular;
  font-weight: 500;
}

.freq-type__example {
  font-size: @font-size-sm;
  color: @text-secondary;
  margin: 0;
  line-height: 1.5;
}

.hot-topics {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.strategy-item {
  display: flex;
  align-items: flex-start;
  gap: 10px;
  margin-bottom: 12px;
  font-size: @font-size-base;
  color: @text-regular;
  line-height: 1.5;

  &:last-child {
    margin-bottom: 0;
  }
}

.strategy-item__num {
  width: 24px;
  height: 24px;
  border-radius: 50%;
  background: @primary-color;
  color: #fff;
  font-size: @font-size-xs;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
}

.focus-actions {
  margin-top: 8px;
  margin-bottom: 16px;
}

.focus-local-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 12px;
  margin-bottom: 12px;
}

.focus-local-alert {
  margin-bottom: 12px;
}

.local-question-item {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 14px 16px;
  border: 1px solid @divider-color;
  border-radius: @border-radius-base;
  margin-bottom: 10px;
  cursor: pointer;
  transition: box-shadow 0.2s, border-color 0.2s;

  &:hover {
    box-shadow: @shadow-popup;
    border-color: fade(@primary-color, 35%);
  }
}

.local-question-item__idx {
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
}

.local-question-item__content {
  flex: 1;
  min-width: 0;
}

.local-question-item__stem {
  font-size: @font-size-base;
  color: @text-regular;
  line-height: 1.6;
}

.local-question-item__meta {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
  margin-top: 8px;
}

.local-question-item__arrow {
  color: @text-secondary;
}
</style>
