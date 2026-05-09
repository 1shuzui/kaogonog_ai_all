<template>
  <div class="training-page page-container">
    <h2>专项训练</h2>
    <p class="training-page__desc">针对薄弱维度进行专项突破，AI智能出题评分</p>

    <div class="dimension-grid">
      <div
        v-for="dim in dimensionList"
        :key="dim.key"
        class="dimension-card card"
        @click="goToDimension(dim.key)"
      >
        <div class="dimension-card__icon" :style="{ background: dim.bgColor }">
          {{ dim.icon }}
        </div>
        <div class="dimension-card__info">
          <h4>{{ dim.name }}</h4>
          <p class="dimension-card__score">满分 {{ dim.maxScore }} 分</p>
          <div class="dimension-card__progress" v-if="getProgress(dim.key).attempts > 0">
            <span class="progress-label">练习 {{ getProgress(dim.key).attempts }} 次</span>
            <span class="progress-best">最佳 {{ getProgress(dim.key).bestScore }} 分</span>
          </div>
          <div class="dimension-card__progress" v-else>
            <span class="progress-label">尚未练习</span>
          </div>
        </div>
        <RightOutlined class="dimension-card__arrow" />
      </div>
    </div>

    <!-- 综合进度 -->
    <div class="card training-overview" v-if="hasAnyProgress">
      <h3>训练概览</h3>
      <div class="overview-grid">
        <div class="overview-item">
          <div class="overview-item__value">{{ totalAttempts }}</div>
          <div class="overview-item__label">总练习次数</div>
        </div>
        <div class="overview-item">
          <div class="overview-item__value">{{ trainedDimensions }}</div>
          <div class="overview-item__label">已训练维度</div>
        </div>
        <div class="overview-item">
          <div class="overview-item__value">{{ overallAvg }}</div>
          <div class="overview-item__label">平均得分率</div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed } from 'vue'
import { useRouter } from 'vue-router'
import { RightOutlined } from '@ant-design/icons-vue'
import { DIMENSIONS } from '@/utils/constants'
import { useTrainingStore } from '@/stores/training'

const router = useRouter()
const trainingStore = useTrainingStore()

const dimensionList = DIMENSIONS.map(d => ({
  ...d,
  icon: getDimIcon(d.key),
  bgColor: getDimBgColor(d.key)
}))

function getDimIcon(key) {
  const icons = { legal: '⚖️', practical: '🛠️', logic: '🧠', expression: '🎤', analysis: '🔍', emergency: '🚨' }
  return icons[key] || '📝'
}

function getDimBgColor(key) {
  const colors = {
    legal: '#F0E6FF', practical: '#E6F7E6', logic: '#E6F0FF',
    expression: '#FFF0E6', analysis: '#E6FAFF', emergency: '#FFE6E6'
  }
  return colors[key] || '#F0F0F0'
}

function getProgress(key) {
  return trainingStore.getDimensionProgress(key)
}

function goToDimension(key) {
  router.push(`/training/${key}`)
}

const hasAnyProgress = computed(() => {
  return DIMENSIONS.some(d => getProgress(d.key).attempts > 0)
})

const totalAttempts = computed(() => {
  return DIMENSIONS.reduce((sum, d) => sum + getProgress(d.key).attempts, 0)
})

const trainedDimensions = computed(() => {
  return DIMENSIONS.filter(d => getProgress(d.key).attempts > 0).length
})

const overallAvg = computed(() => {
  let total = 0, count = 0
  for (const d of DIMENSIONS) {
    const p = getProgress(d.key)
    if (p.attempts > 0) {
      total += (p.totalScore / p.attempts / d.maxScore) * 100
      count++
    }
  }
  return count > 0 ? Math.round(total / count) + '%' : '0%'
})
</script>

<style lang="less" scoped>
@import '@/styles/variables.less';

.training-page {
  h2 {
    font-size: @font-size-xl;
    color: @text-primary;
    margin-bottom: 4px;
  }
}

.training-page__desc {
  font-size: @font-size-sm;
  color: @text-secondary;
  margin-bottom: 16px;
}

.dimension-grid {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.dimension-card {
  display: flex;
  align-items: center;
  padding: 16px;
  cursor: pointer;
  transition: box-shadow 0.2s;

  &:hover {
    box-shadow: @shadow-popup;
  }
}

.dimension-card__icon {
  width: 48px;
  height: 48px;
  border-radius: 12px;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 24px;
  flex-shrink: 0;
  margin-right: 14px;
}

.dimension-card__info {
  flex: 1;
  min-width: 0;

  h4 {
    font-size: @font-size-base;
    color: @text-primary;
    margin-bottom: 2px;
    font-weight: 600;
  }
}

.dimension-card__score {
  font-size: @font-size-xs;
  color: @text-secondary;
  margin-bottom: 4px;
}

.dimension-card__progress {
  display: flex;
  gap: 12px;
  font-size: @font-size-xs;
}

.progress-label {
  color: @text-secondary;
}

.progress-best {
  color: @primary-color;
  font-weight: 500;
}

.dimension-card__arrow {
  color: @text-secondary;
  flex-shrink: 0;
}

.training-overview {
  margin-top: 16px;
  padding: 16px;

  h3 {
    font-size: @font-size-lg;
    color: @text-primary;
    margin-bottom: 14px;
  }
}

.overview-grid {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 10px;
}

.overview-item {
  text-align: center;
}

.overview-item__value {
  font-size: @font-size-xl;
  font-weight: 700;
  color: @primary-color;
}

.overview-item__label {
  font-size: @font-size-xs;
  color: @text-secondary;
  margin-top: 2px;
}
</style>
