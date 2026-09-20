<template>
  <view class="motion-accent" :style="style">
    <view class="motion-accent__art" :class="{ 'motion-accent__art--playing': playing, 'motion-accent__art--static': mode !== 'full' }"><slot /></view>
  </view>
</template>
<script setup>
import { computed, getCurrentInstance, nextTick, onMounted, onBeforeUnmount, ref, watch } from 'vue'
import { useMotion } from '../motion/useMotion'
import { motionStyle } from '../motion/policy.mjs'
const props = defineProps({ active: { type: Boolean, default: true } })
const { proxy } = getCurrentInstance()
const { mode, visible } = useMotion()
const inView = ref(false)
let observer = null
let generation = 0
let mounted = false
const playing = computed(() => visible.value && props.active && inView.value && mode.value === 'full')
const style = computed(() => motionStyle(mode.value))
function stop() { generation += 1; observer?.disconnect(); observer = null; inView.value = false }
async function observe() {
  stop()
  const id = generation
  if (!mounted || !visible.value || !props.active || mode.value !== 'full') return
  await nextTick()
  if (id !== generation) return
  // Unsupported observers degrade to a static illustration, never an endless loop.
  try {
    observer = uni.createIntersectionObserver(proxy, { thresholds: [0, .05] })
    observer.relativeToViewport().observe('.motion-accent', result => {
      if (id === generation) inView.value = result.intersectionRatio > 0
    })
  } catch { stop() }
}
onMounted(() => { mounted = true; observe() })
watch([visible, mode, () => props.active], observe)
onBeforeUnmount(() => { mounted = false; stop() })
</script>
<style scoped>
.motion-accent { display:flex; justify-content:center; align-items:center; }
.motion-accent__art { animation:accent-float var(--motion-float) ease-in-out infinite; animation-play-state:paused; }
.motion-accent__art--playing { animation-play-state:running; }
.motion-accent__art--static { animation:none; transform:none; }
@keyframes accent-float { 0%,100% { transform:translateY(0) rotate(-3deg); } 50% { transform:translateY(-4px) rotate(3deg); } }
</style>
