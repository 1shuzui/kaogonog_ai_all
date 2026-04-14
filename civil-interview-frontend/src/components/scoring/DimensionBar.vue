<template>
  <div class="dimension-bar">
    <div class="dimension-bar__header">
      <span class="dimension-bar__name">{{ name }}</span>
      <span class="dimension-bar__score" :style="{ color: scoreColor }">
        {{ score }}/{{ maxScore }}
      </span>
    </div>
    <div class="dimension-bar__track">
      <div
        class="dimension-bar__fill"
        :style="{ width: percent + '%', background: scoreColor }"
      ></div>
    </div>
  </div>
</template>

<script setup>
import { computed } from 'vue'

const props = defineProps({
  name: { type: String, required: true },
  score: { type: Number, default: 0 },
  maxScore: { type: Number, default: 20 }
})

const percent = computed(() => (props.score / props.maxScore) * 100)
const scoreColor = computed(() => {
  const ratio = props.score / props.maxScore
  if (ratio >= 0.85) return '#389E0D'
  if (ratio >= 0.75) return '#1B5FAA'
  if (ratio >= 0.6) return '#D48806'
  return '#CF1322'
})
</script>

<style lang="less" scoped>
@import '@/styles/variables.less';

.dimension-bar__header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 4px;
}

.dimension-bar__name {
  font-size: @font-size-sm;
  color: @text-regular;
}

.dimension-bar__score {
  font-size: @font-size-sm;
  font-weight: 600;
}

.dimension-bar__track {
  height: 8px;
  background: #F0F0F0;
  border-radius: 4px;
  overflow: hidden;
}

.dimension-bar__fill {
  height: 100%;
  border-radius: 4px;
  transition: width 0.8s ease;
}
</style>
