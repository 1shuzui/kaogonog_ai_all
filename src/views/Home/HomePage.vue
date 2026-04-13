<template>
  <div class="home-page page-container">
    <!-- 快速开始卡片 -->
    <div class="home-hero card">
      <div class="home-hero__info">
        <h1>公考面试AI测评</h1>
        <p>智能评分 / 精准诊断 / 高效提分</p>
        <a-button type="primary" size="large" @click="$router.push('/exam/prepare')">
          <PlayCircleOutlined /> 开始模考
        </a-button>
      </div>
      <div class="home-hero__score" v-if="historyStore.stats">
        <ScoreRing
          :score="historyStore.averageScore"
          :maxScore="100"
          size="medium"
          label="平均分"
        />
      </div>
    </div>

    <!-- 数据概览 -->
    <div class="home-stats" v-if="historyStore.stats">
      <div class="home-stat-item card">
        <div class="home-stat-item__value">{{ historyStore.stats.totalExams }}</div>
        <div class="home-stat-item__label">练习次数</div>
      </div>
      <div class="home-stat-item card">
        <div class="home-stat-item__value">{{ historyStore.bestScore }}</div>
        <div class="home-stat-item__label">最高分</div>
      </div>
      <div class="home-stat-item card">
        <div class="home-stat-item__value" style="font-size: 14px">{{ historyStore.weakestDimension }}</div>
        <div class="home-stat-item__label">薄弱维度</div>
      </div>
    </div>

    <!-- 近期练习记录 -->
    <div class="home-section">
      <div class="home-section__header">
        <h3>近期练习</h3>
        <a-button type="link" @click="$router.push('/history')">查看全部</a-button>
      </div>
      <a-spin :spinning="loading">
        <div v-if="recentRecords.length">
          <div
            v-for="record in recentRecords"
            :key="record.examId"
            class="home-record-item card"
            @click="$router.push(`/result/${record.examId}`)"
          >
            <div class="home-record-item__left">
              <div class="home-record-item__summary">{{ record.questionSummary }}</div>
              <div class="home-record-item__meta">
                <span>{{ formatDate(record.date) }}</span>
                <a-tag :color="gradeColor(record.grade)" size="small">{{ record.grade }}</a-tag>
              </div>
            </div>
            <ScoreRing :score="record.totalScore" :maxScore="record.maxScore" size="small" />
          </div>
        </div>
        <EmptyState v-else text="暂无练习记录，开始第一次模考吧">
          <template #action>
            <a-button type="primary" @click="$router.push('/exam/prepare')">开始模考</a-button>
          </template>
        </EmptyState>
      </a-spin>
    </div>

    <!-- 能力趋势图 -->
    <div class="card home-trend" v-if="historyStore.trendData.length">
      <h3>成绩趋势</h3>
      <div ref="trendChartRef" style="height: 200px"></div>
    </div>

    <!-- 能力总览雷达图 -->
    <div class="card home-radar" v-if="radarDimensions.length">
      <h3>能力总览</h3>
      <RadarChart :dimensions="radarDimensions" size="medium" />
    </div>

    <!-- 薄弱维度分析 -->
    <WeaknessAnalysis
      v-if="historyStore.stats?.dimensionAverages?.length"
      :dimensionAverages="historyStore.stats.dimensionAverages"
    />

    <!-- 智能推荐练习 -->
    <SmartRecommendation
      v-if="historyStore.stats?.dimensionAverages?.length"
      :weakDimensions="weakDimensionKeys"
    />
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onUnmounted } from 'vue'
import { PlayCircleOutlined } from '@ant-design/icons-vue'
import echarts from '@/utils/echarts'
import { useHistoryStore } from '@/stores/history'
import { useUserStore } from '@/stores/user'
import { formatDate } from '@/utils/formatter'
import { GRADE_CONFIG, DIMENSIONS, WEAK_THRESHOLD } from '@/utils/constants'
import ScoreRing from '@/components/common/ScoreRing.vue'
import RadarChart from '@/components/common/RadarChart.vue'
import WeaknessAnalysis from '@/components/common/WeaknessAnalysis.vue'
import SmartRecommendation from '@/components/common/SmartRecommendation.vue'
import EmptyState from '@/components/common/EmptyState.vue'

const historyStore = useHistoryStore()
const userStore = useUserStore()
const loading = ref(true)
const recentRecords = ref([])
const trendChartRef = ref(null)
let chart = null

// Transform dimensionAverages to RadarChart format
const radarDimensions = computed(() => {
  const avgs = historyStore.stats?.dimensionAverages
  if (!avgs?.length) return []
  return avgs.map(d => ({
    name: d.name,
    score: d.avg,
    maxScore: d.maxScore
  }))
})

// Identify weak dimension keys for SmartRecommendation
const weakDimensionKeys = computed(() => {
  const avgs = historyStore.stats?.dimensionAverages
  if (!avgs?.length) return []
  return avgs
    .filter(d => d.maxScore > 0 && (d.avg / d.maxScore * 100) < WEAK_THRESHOLD)
    .map(d => {
      const dim = DIMENSIONS.find(dim => dim.name === d.name)
      return dim ? dim.key : d.name
    })
})

function gradeColor(grade) {
  return GRADE_CONFIG[grade]?.color || '#8C8C8C'
}

onMounted(async () => {
  try {
    await userStore.loadProvinces()
  } catch {
    // 省份加载失败不影响主流程
  }
  try {
    await Promise.all([
      historyStore.fetchRecords({ pageSize: 3 }),
      historyStore.fetchStats(),
      historyStore.fetchTrend()
    ])
  } catch {
    // API 请求失败时不阻塞页面渲染
  }
  recentRecords.value = (historyStore.records || []).slice(0, 3)
  loading.value = false

  // 渲染趋势图
  if (trendChartRef.value && historyStore.trendData.length) {
    chart = echarts.init(trendChartRef.value)
    chart.setOption({
      grid: { top: 10, right: 16, bottom: 24, left: 40 },
      xAxis: {
        type: 'category',
        data: historyStore.trendData.map(d => d.label),
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
        data: historyStore.trendData.map(d => d.score),
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

.home-hero {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 24px;
  background: linear-gradient(135deg, @primary-color 0%, @secondary-blue 100%);
  color: #fff;

  h1 {
    font-size: @font-size-xxl;
    margin-bottom: 4px;
  }
  p {
    opacity: 0.85;
    margin-bottom: 16px;
    font-size: @font-size-sm;
  }
  .ant-btn {
    border-color: #fff;
  }
}

.home-stats {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 10px;
  margin-top: 12px;
}

.home-stat-item {
  text-align: center;
  padding: 12px 8px;
}

.home-stat-item__value {
  font-size: @font-size-xl;
  font-weight: 700;
  color: @primary-color;
}

.home-stat-item__label {
  font-size: @font-size-xs;
  color: @text-secondary;
  margin-top: 2px;
}

.home-section {
  margin-top: 16px;
}

.home-section__header {
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

.home-record-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 14px 16px;
  margin-bottom: 8px;
  cursor: pointer;
  transition: box-shadow 0.2s;

  &:hover {
    box-shadow: @shadow-popup;
  }
}

.home-record-item__summary {
  font-size: @font-size-base;
  color: @text-regular;
  margin-bottom: 4px;
  display: -webkit-box;
  -webkit-line-clamp: 1;
  -webkit-box-orient: vertical;
  overflow: hidden;
}

.home-record-item__meta {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: @font-size-xs;
  color: @text-secondary;
}

.home-trend {
  margin-top: 16px;
  padding: 16px;

  h3 {
    font-size: @font-size-lg;
    color: @text-primary;
    margin-bottom: 12px;
  }
}
</style>
