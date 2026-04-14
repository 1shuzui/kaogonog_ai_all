<template>
  <div class="dim-training page-container">
    <div class="dim-training__header">
      <a-button type="text" @click="$router.back()">
        <LeftOutlined /> 返回
      </a-button>
      <h2>{{ dimensionName }}专项训练</h2>
    </div>

    <!-- 维度进度 -->
    <div class="card dim-progress">
      <div class="dim-progress__icon" :style="{ background: dimBgColor }">{{ dimIcon }}</div>
      <div class="dim-progress__info">
        <div class="dim-progress__stats">
          <span>练习 <strong>{{ progress.attempts }}</strong> 次</span>
          <span>最佳 <strong>{{ progress.bestScore }}</strong> 分</span>
          <span>平均 <strong>{{ avgScore }}</strong> 分</span>
        </div>
        <div v-if="progress.recentScores.length" class="dim-progress__recent">
          近期得分：
          <span v-for="(s, i) in progress.recentScores.slice(-5)" :key="i" class="recent-score">{{ s }}</span>
        </div>
      </div>
    </div>

    <!-- 生成训练题 -->
    <div class="dim-actions">
      <a-space direction="vertical" style="width: 100%">
        <a-button
          type="primary"
          size="large"
          block
          :loading="generating"
          @click="generateQuestions('local')"
        >
          <ThunderboltOutlined /> 匹配本地{{ dimensionName }}题
        </a-button>
        <a-button
          size="large"
          block
          :loading="generating"
          @click="generateQuestions('ai')"
        >
          <ThunderboltOutlined /> AI生成{{ dimensionName }}训练题
        </a-button>
      </a-space>
    </div>

    <!-- 题目列表 -->
    <div v-if="questions.length" class="dim-questions">
      <div class="section-header">
        <h3>训练题目</h3>
        <div class="section-header__actions">
          <a-button type="primary" size="small" @click="startBatchPractice">整组随机作答</a-button>
          <a-button type="link" size="small" @click="generateQuestions(generationMode)">重新生成</a-button>
        </div>
      </div>
      <div
        v-for="(q, idx) in questions"
        :key="q.id"
        class="card question-item"
        @click="startPractice(q)"
      >
        <div class="question-item__idx">{{ idx + 1 }}</div>
        <div class="question-item__content">
          <div class="question-item__stem">{{ q.stem }}</div>
        </div>
        <RightOutlined class="question-item__arrow" />
      </div>
    </div>

    <!-- 提示 -->
    <div class="card dim-tip" v-if="tip">
      <BulbOutlined style="color: #D48806; margin-right: 6px" />
      <span>{{ tip }}</span>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { LeftOutlined, ThunderboltOutlined, RightOutlined, BulbOutlined } from '@ant-design/icons-vue'
import { message } from 'ant-design-vue'
import { DIMENSIONS, DIMENSION_TIPS } from '@/utils/constants'
import { useTrainingStore } from '@/stores/training'
import { generateTrainingQuestions } from '@/api/training'

const route = useRoute()
const router = useRouter()
const trainingStore = useTrainingStore()

const dimensionKey = computed(() => route.params.dimension)
const dimensionInfo = computed(() => DIMENSIONS.find(d => d.key === dimensionKey.value))
const dimensionName = computed(() => dimensionInfo.value?.name || dimensionKey.value)
const tip = computed(() => DIMENSION_TIPS[dimensionName.value] || '')

const dimIcon = computed(() => {
  const icons = { legal: '⚖️', practical: '🛠️', logic: '🧠', expression: '🎤', analysis: '🔍', emergency: '🚨' }
  return icons[dimensionKey.value] || '📝'
})

const dimBgColor = computed(() => {
  const colors = {
    legal: '#F0E6FF', practical: '#E6F7E6', logic: '#E6F0FF',
    expression: '#FFF0E6', analysis: '#E6FAFF', emergency: '#FFE6E6'
  }
  return colors[dimensionKey.value] || '#F0F0F0'
})

const progress = computed(() => trainingStore.getDimensionProgress(dimensionKey.value))

const avgScore = computed(() => {
  const p = progress.value
  if (p.attempts === 0) return 0
  return Math.round(p.totalScore / p.attempts)
})

const generating = ref(false)
const questions = ref([])
const generationMode = ref('local')

async function generateQuestions(sourceMode = 'local') {
  generating.value = true
  generationMode.value = sourceMode
  try {
    questions.value = await generateTrainingQuestions({
      dimension: dimensionKey.value,
      count: 3
    }, sourceMode)
    if (questions.value?.[0]?.generationSource === 'fallback_bank') {
      message.warning(questions.value[0].generationFallbackReason || 'AI 训练题不可用，已回退为本地题库题')
    } else if (sourceMode === 'ai') {
      message.success('已生成 AI 训练题')
    } else {
      message.success('已匹配本地题库题')
    }
  } finally {
    generating.value = false
  }
}

function startPractice(question) {
  // 仅作为页面刷新时的本地缓存，题目本体以后端持久化数据为准
  sessionStorage.setItem('training_question', JSON.stringify(question))
  router.push({ path: '/exam/prepare', query: { questionId: question.id, source: 'training' } })
}

function startBatchPractice() {
  if (!questions.value.length) {
    return
  }
  sessionStorage.setItem('training_question_batch', JSON.stringify(questions.value))
  router.push({ path: '/exam/prepare', query: { source: 'training' } })
}

onMounted(() => {
  if (!dimensionInfo.value) {
    router.replace('/training')
  }
})
</script>

<style lang="less" scoped>
@import '@/styles/variables.less';

.dim-training__header {
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

.dim-progress {
  display: flex;
  align-items: center;
  padding: 16px;
  margin-bottom: 16px;
}

.dim-progress__icon {
  width: 56px;
  height: 56px;
  border-radius: 14px;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 28px;
  flex-shrink: 0;
  margin-right: 16px;
}

.dim-progress__info {
  flex: 1;
}

.dim-progress__stats {
  display: flex;
  gap: 16px;
  font-size: @font-size-sm;
  color: @text-secondary;
  margin-bottom: 6px;

  strong {
    color: @primary-color;
    font-weight: 600;
  }
}

.dim-progress__recent {
  font-size: @font-size-xs;
  color: @text-secondary;
}

.recent-score {
  display: inline-block;
  padding: 1px 6px;
  margin-left: 4px;
  border-radius: 4px;
  background: @bg-light-blue;
  color: @primary-color;
  font-size: @font-size-xs;
  font-weight: 500;
}

.dim-actions {
  margin-bottom: 16px;
}

.dim-questions {
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

.section-header__actions {
  display: flex;
  align-items: center;
  gap: 8px;
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

.dim-tip {
  display: flex;
  align-items: flex-start;
  padding: 14px 16px;
  font-size: @font-size-sm;
  color: @text-regular;
  line-height: 1.5;
}
</style>
