<template>
  <view class="question-card card" @tap="emit('select', question)">
    <view class="question-card__top">
      <view class="question-card__tags">
        <text class="question-card__tag">{{ provinceName }}</text>
        <text class="question-card__tag question-card__tag--blue">{{ categoryName }}</text>
      </view>
      <text class="question-card__points">{{ pointsCount }} 个采分点</text>
    </view>
    <text class="question-card__stem">{{ question?.stem || '暂无题干' }}</text>
    <view v-if="keywords.length" class="question-card__keywords">
      <text v-for="keyword in keywords" :key="keyword" class="question-card__keyword">{{ keyword }}</text>
    </view>
  </view>
</template>

<script setup>
import { computed } from 'vue'
import { getCategoryName, getProvinceName } from '../utils/constants'

const props = defineProps({
  question: {
    type: Object,
    default: () => ({})
  }
})

const emit = defineEmits(['select'])

const provinceName = computed(() => getProvinceName(props.question?.province || 'national'))
const categoryName = computed(() => getCategoryName(props.question?.dimension || props.question?.type || ''))
const pointsCount = computed(() => Array.isArray(props.question?.scoringPoints) ? props.question.scoringPoints.length : 0)
const keywords = computed(() => {
  const source = props.question?.keywords
  if (Array.isArray(source)) return source.slice(0, 4)
  if (source?.scoring) return source.scoring.slice(0, 4)
  return []
})
</script>

<style scoped>
.question-card {
  position: relative;
}

.question-card__top {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 16rpx;
  margin-bottom: 16rpx;
}

.question-card__tags {
  display: flex;
  flex-wrap: wrap;
  gap: 10rpx;
}

.question-card__tag {
  padding: 6rpx 14rpx;
  border-radius: 999rpx;
  background: #eef4ff;
  color: #45617e;
  font-size: 22rpx;
}

.question-card__tag--blue {
  background: #e8f4fd;
  color: #1b5faa;
}

.question-card__points {
  flex-shrink: 0;
  color: #6f7c8f;
  font-size: 22rpx;
}

.question-card__stem {
  display: -webkit-box;
  overflow: hidden;
  color: #1f2b3d;
  font-size: 29rpx;
  line-height: 1.7;
  -webkit-box-orient: vertical;
  -webkit-line-clamp: 4;
}

.question-card__keywords {
  display: flex;
  flex-wrap: wrap;
  gap: 10rpx;
  margin-top: 18rpx;
}

.question-card__keyword {
  padding: 6rpx 12rpx;
  border-radius: 8rpx;
  background: #f6f8fb;
  color: #6f7c8f;
  font-size: 22rpx;
}
</style>
