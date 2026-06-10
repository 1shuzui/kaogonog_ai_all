<!--
智能推荐组件，根据历史表现展示下一步练习建议；无数据时必须可解释降级。

@param: 通过 props、slot 和事件接收页面上下文；不直接拥有业务真源。
@return: 渲染可复用 UI，并通过 emit 或插槽把操作交还给父页面。
@raises: 不主动抛业务异常；异常状态应由父页面、请求层或兜底 UI 承接。
-->
<template>
  <view class="smart-rec card">
    <view class="smart-rec__header">
      <text class="smart-rec__title">智能推荐练习</text>
      <button class="smart-rec__refresh" :loading="loadingRec" @tap="refreshRecommendations">刷新</button>
    </view>
    <text class="smart-rec__source">真实题库推荐 · 按薄弱维度、省份与已练记录筛选</text>

    <view v-if="weakDimensions.length">
      <view v-if="loadingRec" class="smart-rec__loading motion-shimmer">
        <text class="smart-rec__loading-text">正在分析推荐...</text>
      </view>

      <view v-else-if="recommendations.length">
        <view v-for="item in recommendations" :key="item.id" class="smart-rec__item">
          <view class="smart-rec__item-header">
            <text class="smart-rec__dim-tag" :style="{ background: dimColorBg(item.dimension), color: dimColor(item.dimension) }">
              {{ dimName(item.dimension) }}
            </text>
            <text class="smart-rec__reason">{{ item.reason }}</text>
          </view>
          <QuestionCard
            :question="item"
            :show-rich-content="true"
            :collapsed-height="200"
            compact
            @select="startPractice(item)"
          />
        </view>
      </view>

      <view v-else class="smart-rec__empty">
        <text>暂无推荐题目</text>
      </view>
    </view>

    <view v-else class="smart-rec__balanced">
      <text class="smart-rec__balanced-icon">&#10003;</text>
      <text class="smart-rec__balanced-text">各维度表现均衡，继续保持！</text>
    </view>
  </view>
</template>

<script setup>
import { ref, watch, onMounted } from 'vue'
import QuestionCard from './QuestionCard.vue'
import { getRandomQuestions } from '../api/questionBank'
import { getProvinceName } from '../utils/constants'

const props = defineProps({
  weakDimensions: { type: Array, default: () => [] },
  province: { type: String, default: 'national' }
})

const loadingRec = ref(false)
const recommendations = ref([])
const RECOMMENDATION_STORAGE_KEY = 'civil_rec_practiced'

const DIM_COLORS = {
  legal: '#2F7FD6',
  practical: '#389E0D',
  logic: '#722ED1',
  expression: '#D48806',
  analysis: '#13C2C2',
  emergency: '#CF1322'
}

const DIM_COLORS_BG = {
  legal: 'rgba(47, 127, 214, 0.08)',
  practical: 'rgba(56, 142, 13, 0.08)',
  logic: 'rgba(114, 46, 209, 0.08)',
  expression: 'rgba(212, 136, 6, 0.08)',
  analysis: 'rgba(19, 194, 194, 0.08)',
  emergency: 'rgba(207, 19, 34, 0.08)'
}

const DIM_NAMES = {
  legal: '行政思维',
  practical: '实务落地',
  logic: '逻辑结构',
  expression: '语言表达',
  analysis: '综合分析',
  emergency: '应急应变'
}

function dimName(key) {
  return DIM_NAMES[key] || key
}

function dimColor(key) {
  return DIM_COLORS[key] || '#8C8C8C'
}

function dimColorBg(key) {
  return DIM_COLORS_BG[key] || 'rgba(140, 140, 140, 0.08)'
}

function loadPracticedIds() {
  try {
    const raw = uni.getStorageSync(RECOMMENDATION_STORAGE_KEY)
    const parsed = raw ? JSON.parse(raw) : []
    return new Set(Array.isArray(parsed) ? parsed.filter(Boolean) : [])
  } catch {
    return new Set()
  }
}

function markPracticed(questionId) {
  if (!questionId) return
  const ids = loadPracticedIds()
  ids.add(questionId)
  uni.setStorageSync(RECOMMENDATION_STORAGE_KEY, JSON.stringify(Array.from(ids).slice(-300)))
}

async function fetchRecommendations() {
  if (!props.weakDimensions.length) {
    recommendations.value = []
    return
  }
  loadingRec.value = true
  try {
    const results = []
    const practicedIds = loadPracticedIds()
    const dimensions = props.weakDimensions.slice(0, 3).filter(Boolean)
    const list = await getRandomQuestions({
      province: props.province || 'national',
      dimension: dimensions.join(','),
      count: 18
    })

    for (const q of Array.isArray(list) ? list : []) {
      if (!q?.id || practicedIds.has(q.id)) continue
      const dim = q.dimension || dimensions[0] || 'analysis'
      const difficulty = Math.min(5, Math.max(1, (q.scoringPoints?.length || 3)))
      results.push({
        ...q,
        id: q.id,
        stem: q.stem,
        dimension: dim,
        difficulty,
        reason: `${dimName(dim)}维度薄弱，来自真实题库的专项推荐`
      })
    }

    recommendations.value = results.slice(0, 6)
  } catch (e) {
    recommendations.value = []
  } finally {
    loadingRec.value = false
  }
}

function refreshRecommendations() {
  fetchRecommendations()
}

function startPractice(item) {
  markPracticed(item.id)
  uni.navigateTo({ url: `/pages/exam/prepare?questionId=${encodeURIComponent(item.id)}` })
}

onMounted(() => {
  fetchRecommendations()
})

watch(() => props.weakDimensions, () => {
  fetchRecommendations()
}, { deep: true })

watch(() => props.province, () => {
  fetchRecommendations()
})
</script>

<style scoped>
.smart-rec {
  margin-top: 16rpx;
  padding: 24rpx;
}

.smart-rec__header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 12rpx;
}

.smart-rec__title {
  color: #172033;
  font-size: 32rpx;
  font-weight: 700;
}

.smart-rec__refresh {
  padding: 10rpx 24rpx;
  border-radius: 999rpx;
  background: #eef4ff;
  color: #2F7FD6;
  font-size: 24rpx;
  border: none;
  line-height: 1.35;
  transition: transform 160ms ease, opacity 160ms ease, background-color 160ms ease;
}

.smart-rec__refresh:active {
  opacity: 0.9;
  transform: scale(0.96);
}

.smart-rec__source {
  display: block;
  margin-bottom: 18rpx;
  color: #64748B;
  font-size: 22rpx;
}

.smart-rec__loading {
  padding: 40rpx 0;
  border-radius: 16rpx;
  background: #f7fbff;
  text-align: center;
}

.smart-rec__loading-text {
  color: #64748B;
  font-size: 26rpx;
}

.smart-rec__item {
  padding: 20rpx;
  background: linear-gradient(180deg, #ffffff 0%, #f7fbff 100%);
  border-radius: 16rpx;
  margin-bottom: 16rpx;
  border: 1rpx solid #DCEAF7;
  animation: motion-fade-up 220ms ease-out both;
}

.smart-rec__item-header {
  display: flex;
  align-items: center;
  gap: 12rpx;
  margin-bottom: 12rpx;
}

.smart-rec__dim-tag {
  padding: 6rpx 14rpx;
  border-radius: 999rpx;
  font-size: 22rpx;
  flex-shrink: 0;
}

.smart-rec__reason {
  color: #64748B;
  font-size: 22rpx;
  line-height: 1.4;
}

.smart-rec__empty {
  padding: 40rpx 0;
  text-align: center;
  color: #64748B;
  font-size: 26rpx;
}

.smart-rec__balanced {
  padding: 40rpx 0;
  text-align: center;
}

.smart-rec__balanced-icon {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 64rpx;
  height: 64rpx;
  border-radius: 999rpx;
  background: #eaf7e6;
  color: #389e0d;
  font-size: 32rpx;
  font-weight: 800;
  margin-bottom: 12rpx;
  animation: balanced-check-pop 240ms ease-out both;
}

.smart-rec__balanced-text {
  display: block;
  color: #64748B;
  font-size: 26rpx;
}

@keyframes balanced-check-pop {
  from {
    opacity: 0;
    transform: scale(0.72);
  }
  to {
    opacity: 1;
    transform: scale(1);
  }
}
</style>
