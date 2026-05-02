<template>
  <view class="dimension-bars">
    <view v-for="item in normalized" :key="item.key || item.name" class="dimension-bars__item">
      <view class="dimension-bars__head">
        <text class="dimension-bars__name">{{ item.name }}</text>
        <text class="dimension-bars__score">{{ item.score }}/{{ item.maxScore }}</text>
      </view>
      <view class="dimension-bars__track">
        <view
          class="dimension-bars__bar"
          :style="{ width: `${item.percent}%`, background: barColor(item.percent) }"
        />
      </view>
    </view>
  </view>
</template>

<script setup>
import { computed } from 'vue'
import { normalizeDimensions } from '../utils/scoring'

const props = defineProps({
  dimensions: {
    type: Array,
    default: () => []
  }
})

const normalized = computed(() => normalizeDimensions(props.dimensions))

function barColor(percent) {
  if (percent >= 80) return '#389e0d'
  if (percent >= 60) return '#1b5faa'
  if (percent >= 40) return '#d48806'
  return '#cf1322'
}
</script>

<style scoped>
.dimension-bars {
  display: flex;
  flex-direction: column;
  gap: 18rpx;
}

.dimension-bars__head {
  display: flex;
  justify-content: space-between;
  margin-bottom: 8rpx;
}

.dimension-bars__name {
  color: #2a3648;
  font-size: 26rpx;
  font-weight: 600;
}

.dimension-bars__score {
  color: #6f7c8f;
  font-size: 24rpx;
}

.dimension-bars__track {
  overflow: hidden;
  width: 100%;
  height: 12rpx;
  border-radius: 999rpx;
  background: #edf2f7;
}

.dimension-bars__bar {
  height: 100%;
  border-radius: 999rpx;
}
</style>
