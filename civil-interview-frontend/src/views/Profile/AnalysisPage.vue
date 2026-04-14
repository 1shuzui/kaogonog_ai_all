<template>
  <div class="analysis-page page-container">
    <div class="analysis-header">
      <a-button type="text" @click="$router.back()">
        <LeftOutlined /> 返回
      </a-button>
      <h2>个人情况分析</h2>
    </div>

    <a-spin :spinning="loading">
      <template v-if="stats">
        <!-- 综合评估 -->
        <div class="card analysis-overview">
          <div class="analysis-overview__score">
            <ScoreRing :score="stats.avgScore" :maxScore="100" size="large" label="平均分" />
          </div>
          <div class="analysis-overview__info">
            <div class="overview-row">
              <span>练习次数</span>
              <strong>{{ stats.totalExams }}</strong>
            </div>
            <div class="overview-row">
              <span>最高分</span>
              <strong>{{ stats.bestScore }}</strong>
            </div>
            <div class="overview-row">
              <span>薄弱维度</span>
              <strong class="weak-dim">{{ stats.weakestDimension || '暂无' }}</strong>
            </div>
          </div>
        </div>

        <!-- 能力雷达图 -->
        <div class="card analysis-section" v-if="radarDimensions.length">
          <h3>能力维度分析</h3>
          <RadarChart :dimensions="radarDimensions" size="medium" />
        </div>

        <!-- 各维度详情 -->
        <div class="card analysis-section" v-if="stats.dimensionAverages?.length">
          <h3>维度表现</h3>
          <div v-for="d in stats.dimensionAverages" :key="d.name" class="dim-detail">
            <div class="dim-detail__header">
              <span class="dim-detail__name">{{ d.name }}</span>
              <span class="dim-detail__score">{{ d.avg }} / {{ d.maxScore }}</span>
            </div>
            <a-progress
              :percent="Math.round((d.avg / d.maxScore) * 100)"
              :stroke-color="getProgressColor(d.avg, d.maxScore)"
              size="small"
            />
            <p class="dim-detail__tip">{{ getDimTip(d.name) }}</p>
          </div>
        </div>

        <!-- 成绩趋势 -->
        <div class="card analysis-section" v-if="trendData.length">
          <h3>成绩趋势</h3>
          <div ref="trendChartRef" style="height: 200px"></div>
        </div>

        <!-- 薄弱维度分析 -->
        <WeaknessAnalysis
          v-if="stats.dimensionAverages?.length"
          :dimensionAverages="stats.dimensionAverages"
        />

        <!-- 训练进度 -->
        <div class="card analysis-section" v-if="hasTrainingProgress">
          <h3>专项训练进度</h3>
          <div v-for="dim in trainedDimensions" :key="dim.key" class="training-stat">
            <div class="training-stat__header">
              <span>{{ dim.name }}</span>
              <span class="training-stat__count">{{ dim.attempts }} 次</span>
            </div>
            <div class="training-stat__scores">
              <span>平均 {{ dim.avgScore }} 分</span>
              <span>最佳 {{ dim.bestScore }} 分</span>
            </div>
          </div>
        </div>
      </template>

      <EmptyState v-else-if="!loading" text="暂无练习数据，开始你的第一次模考吧" />
    </a-spin>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onUnmounted } from 'vue'
import { LeftOutlined } from '@ant-design/icons-vue'
import echarts from '@/utils/echarts'
import { useHistoryStore } from '@/stores/history'
import { useTrainingStore } from '@/stores/training'
import { DIMENSIONS, DIMENSION_TIPS } from '@/utils/constants'
import RadarChart from '@/components/common/RadarChart.vue'
import ScoreRing from '@/components/common/ScoreRing.vue'
import WeaknessAnalysis from '@/components/common/WeaknessAnalysis.vue'
import EmptyState from '@/components/common/EmptyState.vue'

const historyStore = useHistoryStore()
const trainingStore = useTrainingStore()
const loading = ref(true)
const trendChartRef = ref(null)
let chart = null

const stats = computed(() => historyStore.stats)
const trendData = computed(() => historyStore.trendData || [])

const radarDimensions = computed(() => {
  const avgs = stats.value?.dimensionAverages
  if (!avgs?.length) return []
  return avgs.map(d => ({
    name: d.name,
    score: d.avg,
    maxScore: d.maxScore
  }))
})

const hasTrainingProgress = computed(() => {
  return DIMENSIONS.some(d => {
    const p = trainingStore.getDimensionProgress(d.key)
    return p.attempts > 0
  })
})

const trainedDimensions = computed(() => {
  return DIMENSIONS
    .map(d => {
      const p = trainingStore.getDimensionProgress(d.key)
      return {
        key: d.key,
        name: d.name,
        attempts: p.attempts,
        bestScore: p.bestScore,
        avgScore: p.attempts > 0 ? Math.round(p.totalScore / p.attempts) : 0
      }
    })
    .filter(d => d.attempts > 0)
})

function getProgressColor(score, maxScore) {
  const ratio = score / maxScore
  if (ratio >= 0.8) return '#389E0D'
  if (ratio >= 0.6) return '#1B5FAA'
  if (ratio >= 0.4) return '#D48806'
  return '#CF1322'
}

function getDimTip(name) {
  return DIMENSION_TIPS[name] || ''
}

onMounted(async () => {
  await Promise.all([
    historyStore.fetchStats(),
    historyStore.fetchTrend()
  ])
  loading.value = false

  // 渲染趋势图
  if (trendChartRef.value && trendData.value.length) {
    chart = echarts.init(trendChartRef.value)
    chart.setOption({
      grid: { top: 10, right: 16, bottom: 24, left: 40 },
      xAxis: {
        type: 'category',
        data: trendData.value.map(d => d.label),
        axisLabel: { fontSize: 11, color: '#8C8C8C' },
        axisLine: { lineStyle: { color: '#E8E8E8' } }
      },
      yAxis: {
        type: 'value',
        min: 40,
        max: 100,
        axisLabel: { fontSize: 11, color: '#8C8C8C' },
        splitLine: { lineStyle: { color: '#F0F0F0' } }
      },
      series: [{
        type: 'line',
        data: trendData.value.map(d => d.score),
        smooth: true,
        lineStyle: { color: '#1B5FAA', width: 2 },
        itemStyle: { color: '#1B5FAA' },
        areaStyle: {
          color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
            { offset: 0, color: 'rgba(27, 95, 170, 0.25)' },
            { offset: 1, color: 'rgba(27, 95, 170, 0.02)' }
          ])
        }
      }]
    })
  }
})

onUnmounted(() => {
  chart?.dispose()
})
</script>

<style lang="less" scoped>
@import '@/styles/variables.less';

.analysis-header {
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

.analysis-overview {
  display: flex;
  align-items: center;
  padding: 20px 16px;
  margin-bottom: 12px;
}

.analysis-overview__score {
  margin-right: 24px;
}

.analysis-overview__info {
  flex: 1;
}

.overview-row {
  display: flex;
  justify-content: space-between;
  padding: 6px 0;
  font-size: @font-size-sm;
  color: @text-secondary;
  border-bottom: 1px solid @divider-color;

  &:last-child {
    border-bottom: none;
  }

  strong {
    color: @text-primary;
    font-weight: 600;
  }
}

.weak-dim {
  color: @score-red !important;
}

.analysis-section {
  padding: 16px;
  margin-bottom: 12px;

  h3 {
    font-size: @font-size-lg;
    color: @text-primary;
    margin-bottom: 14px;
  }
}

.dim-detail {
  margin-bottom: 16px;

  &:last-child {
    margin-bottom: 0;
  }
}

.dim-detail__header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 4px;
}

.dim-detail__name {
  font-size: @font-size-base;
  color: @text-regular;
  font-weight: 500;
}

.dim-detail__score {
  font-size: @font-size-sm;
  color: @primary-color;
  font-weight: 600;
}

.dim-detail__tip {
  font-size: @font-size-xs;
  color: @text-secondary;
  margin-top: 4px;
  margin-bottom: 0;
  line-height: 1.5;
}

.training-stat {
  padding: 10px 0;
  border-bottom: 1px solid @divider-color;

  &:last-child {
    border-bottom: none;
  }
}

.training-stat__header {
  display: flex;
  justify-content: space-between;
  font-size: @font-size-base;
  color: @text-regular;
  margin-bottom: 4px;
}

.training-stat__count {
  color: @primary-color;
  font-weight: 500;
}

.training-stat__scores {
  display: flex;
  gap: 16px;
  font-size: @font-size-xs;
  color: @text-secondary;
}
</style>
