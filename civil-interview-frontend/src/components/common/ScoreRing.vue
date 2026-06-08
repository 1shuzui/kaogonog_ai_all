<!--
这个分数环组件突出总分或维度分，统一结果页、首页概览和小程序卡片里的分数视觉。

@param: 无；页面运行时从 props、路由参数、Pinia 状态和用户点击中拿数据。
@return: 渲染当前业务界面，并把按钮、表单或跳转事件交给既有流程处理。
@raises: 不主动抛业务异常；接口失败、未登录和权限不足由请求层或页面提示承接。
-->
<template>
  <div class="score-ring" :style="ringStyle">
    <svg :width="svgSize" :height="svgSize" viewBox="0 0 120 120">
      <circle cx="60" cy="60" :r="radius" fill="none"
        :stroke="trackColor" :stroke-width="strokeWidth" />
      <circle cx="60" cy="60" :r="radius" fill="none"
        :stroke="activeColor" :stroke-width="strokeWidth"
        :stroke-dasharray="circumference"
        :stroke-dashoffset="dashOffset"
        stroke-linecap="round"
        transform="rotate(-90 60 60)"
        class="score-ring__progress" />
    </svg>
    <div class="score-ring__content">
      <div class="score-ring__score" :style="{ color: activeColor }">{{ score }}</div>
      <div class="score-ring__label" v-if="label">{{ label }}</div>
    </div>
  </div>
</template>

<script setup>
import { computed } from 'vue'
import { getGrade } from '@/utils/constants'

const props = defineProps({
  score: { type: Number, default: 0 },
  maxScore: { type: Number, default: 100 },
  size: { type: String, default: 'medium' },
  label: { type: String, default: '' }
})

const sizeMap = { small: 80, medium: 120, large: 160 }
const svgSize = computed(() => sizeMap[props.size] || 120)
const radius = 48
const strokeWidth = 8
const circumference = 2 * Math.PI * radius
const percent = computed(() => Math.min(props.score / props.maxScore, 1))
const dashOffset = computed(() => circumference * (1 - percent.value))
const trackColor = '#E8E8E8'
const activeColor = computed(() => getGrade(props.score, props.maxScore).color)
const ringStyle = computed(() => ({
  width: `${svgSize.value}px`,
  height: `${svgSize.value}px`
}))
</script>

<style lang="less" scoped>
.score-ring {
  position: relative;
  display: inline-flex;
  align-items: center;
  justify-content: center;
}

.score-ring__progress {
  transition: stroke-dashoffset 1s ease;
}

.score-ring__content {
  position: absolute;
  text-align: center;
}

.score-ring__score {
  font-size: 24px;
  font-weight: 700;
  line-height: 1;
  transition: color 0.3s ease;
}

.score-ring__label {
  font-size: 11px;
  color: #8C8C8C;
  margin-top: 2px;
}
</style>
