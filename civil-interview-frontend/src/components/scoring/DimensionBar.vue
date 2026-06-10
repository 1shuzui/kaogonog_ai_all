<!--
能力维度条组件，展示评分后的能力表现，避免与题型训练分类混用。

@param: 通过 props、slot 和事件接收页面上下文；不直接拥有业务真源。
@return: 渲染可复用 UI，并通过 emit 或插槽把操作交还给父页面。
@raises: 不主动抛业务异常；异常状态应由父页面、请求层或兜底 UI 承接。
-->
<template>
  <div class="dimension-bar" :class="{ 'dimension-bar--compact': compact }">
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
  maxScore: { type: Number, default: 20 },
  compact: { type: Boolean, default: false }
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

.dimension-bar--compact {
  .dimension-bar__header {
    margin-bottom: 3px;
  }

  .dimension-bar__name,
  .dimension-bar__score {
    font-size: @font-size-xs;
  }

  .dimension-bar__track {
    height: 6px;
    border-radius: 999px;
  }

  .dimension-bar__fill {
    border-radius: 999px;
  }
}
</style>
