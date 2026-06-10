<!--
倒计时组件，用于考场和准备流程展示剩余时间，避免多个页面各自实现计时格式。

@param: 通过 props、slot 和事件接收页面上下文；不直接拥有业务真源。
@return: 渲染可复用 UI，并通过 emit 或插槽把操作交还给父页面。
@raises: 不主动抛业务异常；异常状态应由父页面、请求层或兜底 UI 承接。
-->
<template>
  <div class="countdown-timer" :class="[`countdown-timer--${mode}`, { 'countdown-timer--blink': props.remaining <= 10 && props.remaining > 0, 'countdown-timer--warning': props.remaining <= 30 }]">
    <svg width="80" height="80" viewBox="0 0 80 80">
      <circle cx="40" cy="40" r="34" fill="none" stroke="#E8E8E8" stroke-width="6" />
      <circle cx="40" cy="40" r="34" fill="none"
        :stroke="ringColor" stroke-width="6"
        :stroke-dasharray="circumference"
        :stroke-dashoffset="dashOffset"
        stroke-linecap="round"
        transform="rotate(-90 40 40)"
        class="countdown-timer__ring" />
    </svg>
    <div class="countdown-timer__text">
      <div class="countdown-timer__time">{{ formattedTime }}</div>
      <div class="countdown-timer__label">{{ modeLabel }}</div>
    </div>
  </div>
</template>

<script setup>
import { computed } from 'vue'
import { formatTime } from '@/utils/formatter'

const props = defineProps({
  remaining: { type: Number, default: 0 },
  total: { type: Number, default: 0 },
  mode: { type: String, default: 'prep' }
})

const radius = 34
const circumference = 2 * Math.PI * radius
const progress = computed(() => props.total > 0 ? props.remaining / props.total : 0)
const dashOffset = computed(() => circumference * (1 - progress.value))
const formattedTime = computed(() => formatTime(props.remaining))
const modeLabel = computed(() => props.mode === 'prep' ? '准备时间' : '作答时间')
const ringColor = computed(() => {
  if (props.remaining <= 10) return '#CF1322'
  if (props.remaining <= 30) return '#D48806'
  return props.mode === 'prep' ? '#2B7FD4' : '#389E0D'
})
</script>

<style lang="less" scoped>
.countdown-timer {
  position: relative;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 80px;
  height: 80px;
}

.countdown-timer__ring {
  transition: stroke-dashoffset 0.3s linear, stroke 0.3s;
}

.countdown-timer__text {
  position: absolute;
  text-align: center;
}

.countdown-timer__time {
  font-size: 18px;
  font-weight: 700;
  color: #fff;
  font-variant-numeric: tabular-nums;
}

.countdown-timer__label {
  font-size: 10px;
  color: rgba(255, 255, 255, 0.7);
}

/* 30秒警告 - 时间文字变红 */
.countdown-timer--warning .countdown-timer__time {
  color: #CF1322;
}

/* 10秒闪烁 */
.countdown-timer--blink {
  animation: blink-warning 0.8s ease-in-out infinite;
}

@keyframes blink-warning {
  0%, 100% { opacity: 1; }
  50% { opacity: 0.4; }
}
</style>
