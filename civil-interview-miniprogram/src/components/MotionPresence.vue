<template>
  <view v-if="state.mounted" class="motion-presence" :class="[`motion-presence--${state.phase}`, { 'motion-presence--layer': layer }]" :style="style">
    <slot />
  </view>
</template>
<script setup>
import { computed, onBeforeUnmount, ref, watch } from 'vue'
import { createPresence } from '../motion/presence.mjs'
import { useMotion } from '../motion/useMotion'
import { motionStyle } from '../motion/policy.mjs'
import tokens from '../motion/tokens.json'
const props = defineProps({ show: Boolean, layer: Boolean })
const { mode, visible } = useMotion()
const state = ref({ mounted: false, phase: 'hidden', id: 0 })
const presence = createPresence({ publish: value => { state.value = value } })
const style = computed(() => motionStyle(mode.value) + `pointer-events:${state.value.interactive ? 'auto' : 'none'};`)
watch([() => props.show, mode, visible], ([show, setting, active]) => {
  const duration = !active || setting === 'off' ? 0 : setting === 'reduced' ? 100 : show ? tokens.enter : tokens.exit
  presence.set(show, duration)
}, { immediate: true })
// The tokenized shared-duration timer is authoritative: bubbled/old animationend
// events must never finish a new transition. CSS runs frames, JS only its edges.
onBeforeUnmount(() => presence.dispose())
</script>
<style scoped>
.motion-presence--layer { position:fixed; top:0; right:0; bottom:0; left:0; z-index:2200; }
.motion-presence--entering { animation:presence-in var(--motion-enter) var(--motion-ease) both; }
.motion-presence--leaving { animation:presence-out var(--motion-exit) ease-out both; }
@keyframes presence-in { from { opacity:0; transform:translateY(var(--motion-offset)); } to { opacity:1; transform:translateY(0); } }
@keyframes presence-out { from { opacity:1; transform:translateY(0); } to { opacity:0; transform:translateY(calc(-1 * var(--motion-offset))); } }
</style>
