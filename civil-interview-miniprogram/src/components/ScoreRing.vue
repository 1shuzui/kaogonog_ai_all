<template>
  <view class="score-ring" :style="{ width: sizeValue, height: sizeValue }">
    <view
      class="score-ring__track"
      :style="{
        background: `conic-gradient(${color} ${percent}%, #edf2f7 0)`
      }"
    >
      <view class="score-ring__inner">
        <text class="score-ring__score">{{ displayScore }}</text>
        <text class="score-ring__label">{{ label }}</text>
      </view>
    </view>
  </view>
</template>

<script setup>
import { computed } from 'vue'
import { formatScore } from '../utils/format'

const props = defineProps({
  score: {
    type: Number,
    default: 0
  },
  maxScore: {
    type: Number,
    default: 100
  },
  size: {
    type: String,
    default: 'large'
  },
  label: {
    type: String,
    default: '得分'
  },
  color: {
    type: String,
    default: '#1b5faa'
  }
})

const percent = computed(() => {
  const value = props.maxScore > 0 ? (props.score / props.maxScore) * 100 : 0
  return Math.max(0, Math.min(100, Math.round(value)))
})

const displayScore = computed(() => formatScore(props.score))

const sizeValue = computed(() => {
  if (props.size === 'small') return '112rpx'
  if (props.size === 'medium') return '156rpx'
  return '196rpx'
})
</script>

<style scoped>
.score-ring {
  flex-shrink: 0;
}

.score-ring__track {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 100%;
  height: 100%;
  border-radius: 999rpx;
}

.score-ring__inner {
  display: flex;
  align-items: center;
  flex-direction: column;
  justify-content: center;
  width: calc(100% - 22rpx);
  height: calc(100% - 22rpx);
  border-radius: 999rpx;
  background: #ffffff;
}

.score-ring__score {
  color: #1a1a2e;
  font-size: 36rpx;
  font-weight: 800;
  line-height: 1.1;
}

.score-ring__label {
  margin-top: 4rpx;
  color: #6f7c8f;
  font-size: 22rpx;
}
</style>
