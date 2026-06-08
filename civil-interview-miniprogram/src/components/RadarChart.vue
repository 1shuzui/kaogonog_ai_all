<!--
这个图表组件原用于能力雷达展示；当前重点分析已隐藏雷达，保留组件是为了历史页面或后续恢复时复用。

@param: 无；页面运行时从 props、路由参数、Pinia 状态和用户点击中拿数据。
@return: 渲染当前业务界面，并把按钮、表单或跳转事件交给既有流程处理。
@raises: 不主动抛业务异常；接口失败、未登录和权限不足由请求层或页面提示承接。
-->
<template>
  <view class="radar-chart" :style="containerStyle">
    <canvas
      :id="canvasId"
      :style="{ width: canvasWidth + 'px', height: canvasHeight + 'px' }"
      type="2d"
    />
  </view>
</template>

<script setup>
import { computed, ref, watch, onMounted, nextTick } from 'vue'

const props = defineProps({
  dimensions: { type: Array, default: () => [] },
  size: { type: String, default: 'medium' }
})

const canvasId = `radar-canvas-${Math.random().toString(36).slice(2, 8)}`
const sizeMap = { small: 240, medium: 320, large: 400 }
const canvasWidth = computed(() => sizeMap[props.size] || 320)
const canvasHeight = computed(() => canvasWidth.value)
const containerStyle = computed(() => ({
  width: `${canvasWidth.value}rpx`,
  height: `${canvasHeight.value}rpx`
}))

function dpr() {
  const sys = uni.getSystemInfoSync()
  return sys.pixelRatio || 2
}

function draw() {
  nextTick(() => {
    const query = uni.createSelectorQuery()
    query.select(`#${canvasId}`).fields({ node: true, size: true }).exec((res) => {
      const node = res?.[0]
      if (!node?.node) return
      const canvas = node.node
      const ctx = canvas.getContext('2d')
      const w = node.width
      const h = node.height
      const scale = dpr()
      canvas.width = w * scale
      canvas.height = h * scale
      ctx.scale(scale, scale)

      const dims = props.dimensions
      if (!dims.length) return

      const cx = w / 2
      const cy = h / 2
      const radius = Math.min(cx, cy) * 0.6
      const count = dims.length
      if (count < 3) return

      // Background grid
      const levels = 4
      for (let l = 1; l <= levels; l++) {
        ctx.beginPath()
        for (let i = 0; i < count; i++) {
          const angle = (Math.PI * 2 * i) / count - Math.PI / 2
          const r = (radius / levels) * l
          const x = cx + r * Math.cos(angle)
          const y = cy + r * Math.sin(angle)
          if (i === 0) ctx.moveTo(x, y)
          else ctx.lineTo(x, y)
        }
        ctx.closePath()
        ctx.strokeStyle = 'rgba(27, 95, 170, 0.12)'
        ctx.lineWidth = 1
        ctx.stroke()
        ctx.fillStyle = l % 2 === 0 ? 'rgba(27, 95, 170, 0.02)' : 'rgba(27, 95, 170, 0.04)'
        ctx.fill()
      }

      // Axis lines
      for (let i = 0; i < count; i++) {
        const angle = (Math.PI * 2 * i) / count - Math.PI / 2
        ctx.beginPath()
        ctx.moveTo(cx, cy)
        ctx.lineTo(cx + radius * Math.cos(angle), cy + radius * Math.sin(angle))
        ctx.strokeStyle = 'rgba(27, 95, 170, 0.12)'
        ctx.lineWidth = 1
        ctx.stroke()
      }

      // Data polygon
      ctx.beginPath()
      for (let i = 0; i < count; i++) {
        const d = dims[i]
        const ratio = d.maxScore > 0 ? Math.min(1, d.score / d.maxScore) : 0
        const angle = (Math.PI * 2 * i) / count - Math.PI / 2
        const r = radius * ratio
        const x = cx + r * Math.cos(angle)
        const y = cy + r * Math.sin(angle)
        if (i === 0) ctx.moveTo(x, y)
        else ctx.lineTo(x, y)
      }
      ctx.closePath()
      ctx.fillStyle = 'rgba(27, 95, 170, 0.18)'
      ctx.fill()
      ctx.strokeStyle = '#1B5FAA'
      ctx.lineWidth = 2
      ctx.stroke()

      // Data points
      for (let i = 0; i < count; i++) {
        const d = dims[i]
        const ratio = d.maxScore > 0 ? Math.min(1, d.score / d.maxScore) : 0
        const angle = (Math.PI * 2 * i) / count - Math.PI / 2
        const r = radius * ratio
        const x = cx + r * Math.cos(angle)
        const y = cy + r * Math.sin(angle)
        ctx.beginPath()
        ctx.arc(x, y, 4, 0, Math.PI * 2)
        ctx.fillStyle = '#1B5FAA'
        ctx.fill()
      }

      // Labels
      ctx.fillStyle = '#555'
      ctx.font = `${props.size === 'small' ? 10 : 12}px sans-serif`
      ctx.textAlign = 'center'
      ctx.textBaseline = 'middle'
      for (let i = 0; i < count; i++) {
        const d = dims[i]
        const label = `${d.name}\n${d.score}/${d.maxScore}`
        const angle = (Math.PI * 2 * i) / count - Math.PI / 2
        const labelR = radius + 28
        const lx = cx + labelR * Math.cos(angle)
        const ly = cy + labelR * Math.sin(angle)
        const lines = label.split('\n')
        lines.forEach((line, li) => {
          ctx.fillText(line, lx, ly + li * 14)
        })
      }
    })
  })
}

onMounted(() => {
  draw()
})

watch(() => props.dimensions, () => {
  draw()
}, { deep: true })
</script>

<style scoped>
.radar-chart {
  margin: 0 auto;
}
</style>
