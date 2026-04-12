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
