<!--
音频波形组件，用视觉反馈降低录音等待焦虑，不参与实际评分。

@param: 通过 props、slot 和事件接收页面上下文；不直接拥有业务真源。
@return: 渲染可复用 UI，并通过 emit 或插槽把操作交还给父页面。
@raises: 不主动抛业务异常；异常状态应由父页面、请求层或兜底 UI 承接。
-->
<template>
  <div class="audio-waveform">
    <canvas ref="canvasRef" :width="width" :height="height"></canvas>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { useAudioVisualizer } from '@/composables/useAudioVisualizer'

const props = defineProps({
  stream: { type: Object, default: null },
  active: { type: Boolean, default: false },
  width: { type: Number, default: 320 },
  height: { type: Number, default: 60 }
})

const { canvasRef, start, stop } = useAudioVisualizer()

// 使用 watch 而非 watchEffect 来控制
import { watch } from 'vue'

watch([() => props.stream, () => props.active], ([stream, active]) => {
  if (stream && active) {
    start(stream)
  } else {
    stop()
  }
})
</script>

<style scoped>
.audio-waveform {
  width: 100%;
  display: flex;
  justify-content: center;

  canvas {
    border-radius: 6px;
    max-width: 100%;
  }
}
</style>
