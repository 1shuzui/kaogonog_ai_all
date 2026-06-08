<!--
这个波形组件给录音过程提供可视反馈，帮助用户确认麦克风确实在收音。

@param: 无；页面运行时从 props、路由参数、Pinia 状态和用户点击中拿数据。
@return: 渲染当前业务界面，并把按钮、表单或跳转事件交给既有流程处理。
@raises: 不主动抛业务异常；接口失败、未登录和权限不足由请求层或页面提示承接。
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
