<template>
  <div class="weakness-analysis card">
    <h3 class="weakness-analysis__title">
      <ExclamationCircleOutlined /> 薄弱维度分析
    </h3>
    <div v-if="sortedDimensions.length" class="weakness-analysis__list">
      <div
        v-for="dim in sortedDimensions"
        :key="dim.name"
        class="weakness-analysis__item"
      >
        <div class="weakness-analysis__header">
          <span class="weakness-analysis__name">{{ dim.name }}</span>
          <span
            class="weakness-analysis__percent"
            :class="{ 'is-weak': dim.isWeak }"
          >
            {{ dim.percent }}%
          </span>
        </div>
        <a-progress
          :percent="dim.percent"
          :showInfo="false"
          :strokeColor="dim.isWeak ? '#CF1322' : '#1B5FAA'"
          size="small"
        />
        <div v-if="dim.isWeak && dim.tip" class="weakness-analysis__tip">
          <BulbOutlined /> {{ dim.tip }}
        </div>
      </div>
    </div>
    <a-empty v-else description="暂无数据" :image="false" />
  </div>
</template>

<script setup>
import { computed } from 'vue'
import { ExclamationCircleOutlined, BulbOutlined } from '@ant-design/icons-vue'
import { DIMENSION_TIPS, WEAK_THRESHOLD } from '@/utils/constants'

const props = defineProps({
  dimensionAverages: { type: Array, default: () => [] }
})

const sortedDimensions = computed(() => {
  if (!props.dimensionAverages.length) return []
  return props.dimensionAverages
    .map(d => {
      const percent = d.maxScore > 0 ? Math.round((d.avg / d.maxScore) * 100) : 0
      return {
        name: d.name,
        avg: d.avg,
        maxScore: d.maxScore,
        percent,
        isWeak: percent < WEAK_THRESHOLD,
        tip: DIMENSION_TIPS[d.name] || ''
      }
    })
    .sort((a, b) => a.percent - b.percent)
})
</script>

<style lang="less" scoped>
@import '@/styles/variables.less';

.weakness-analysis {
  margin-top: 16px;
  padding: 16px;
}

.weakness-analysis__title {
  font-size: @font-size-lg;
  color: @text-primary;
  margin-bottom: 16px;
}

.weakness-analysis__item {
  margin-bottom: 14px;
}

.weakness-analysis__header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 4px;
}

.weakness-analysis__name {
  font-size: @font-size-base;
  color: @text-regular;
}

.weakness-analysis__percent {
  font-size: @font-size-sm;
  font-weight: 600;
  color: @primary-color;

  &.is-weak {
    color: @score-red;
  }
}

.weakness-analysis__tip {
  margin-top: 6px;
  padding: 8px 12px;
  background: fade(@score-gold, 8%);
  border-left: 3px solid @score-gold;
  border-radius: 4px;
  font-size: @font-size-xs;
  color: @text-secondary;
  line-height: 1.6;
}
</style>
