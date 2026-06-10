<!--
雷达图组件，曾用于能力维度展示；数据不足时应隐藏或降级，不能用题型分类凑维度。

@param: 通过 props、slot 和事件接收页面上下文；不直接拥有业务真源。
@return: 渲染可复用 UI，并通过 emit 或插槽把操作交还给父页面。
@raises: 不主动抛业务异常；异常状态应由父页面、请求层或兜底 UI 承接。
-->
<template>
  <div class="radar-chart" ref="chartRef"></div>
</template>

<script setup>
import { ref, onMounted, onUnmounted, watch } from 'vue'
import * as echarts from 'echarts'

const props = defineProps({
  dimensions: { type: Array, default: () => [] },
  size: { type: String, default: 'medium' },
  animated: { type: Boolean, default: true }
})

const chartRef = ref(null)
let chart = null
let resizeObserver = null

const sizeMap = { small: 200, medium: 300, large: 400 }

function renderChart() {
  if (!chart || !props.dimensions.length) return

  const indicator = props.dimensions.map(d => ({
    name: `${d.name}\n${d.score}/${d.maxScore}`,
    max: d.maxScore
  }))
  const values = props.dimensions.map(d => d.score)

  chart.setOption({
    radar: {
      indicator,
      shape: 'polygon',
      radius: '65%',
      axisName: {
        color: '#555',
        fontSize: props.size === 'small' ? 10 : 12
      },
      splitArea: {
        areaStyle: {
          color: ['rgba(27, 95, 170, 0.02)', 'rgba(27, 95, 170, 0.05)']
        }
      },
      splitLine: {
        lineStyle: { color: 'rgba(27, 95, 170, 0.15)' }
      },
      axisLine: {
        lineStyle: { color: 'rgba(27, 95, 170, 0.15)' }
      }
    },
    series: [{
      type: 'radar',
      data: [{
        value: values,
        areaStyle: {
          color: 'rgba(27, 95, 170, 0.25)'
        },
        lineStyle: {
          color: '#1B5FAA',
          width: 2
        },
        itemStyle: {
          color: '#1B5FAA'
        }
      }],
      animationDuration: props.animated ? 1000 : 0
    }]
  })
}

onMounted(() => {
  const height = sizeMap[props.size] || 300
  chartRef.value.style.height = `${height}px`
  chart = echarts.init(chartRef.value)
  renderChart()

  resizeObserver = new ResizeObserver(() => chart?.resize())
  resizeObserver.observe(chartRef.value)
})

onUnmounted(() => {
  resizeObserver?.disconnect()
  chart?.dispose()
})

watch(() => props.dimensions, renderChart, { deep: true })
</script>

<style scoped>
.radar-chart {
  width: 100%;
}
</style>
