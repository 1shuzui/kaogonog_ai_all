<template>
  <view class="motion-summary" :class="{ 'motion-summary--compact': compact }" :style="style" :aria-hidden="!compact">
    <view class="motion-summary__copy"><text class="motion-summary__title">{{ title }}</text><text v-if="detail" class="motion-summary__detail">{{ detail }}</text></view>
    <button class="motion-summary__top" :disabled="!compact" hover-class="motion-summary__pressed" @tap="backToTop">回顶部 ↑</button>
  </view>
</template>
<script setup>
import { computed } from 'vue'
import { useMotion } from '../motion/useMotion'
import { motionStyle } from '../motion/policy.mjs'
const props = defineProps({ compact: Boolean, title: String, detail: String })
const { mode } = useMotion()
const style = computed(() => motionStyle(mode.value))
function backToTop() { uni.pageScrollTo({ scrollTop: 0, duration: mode.value === 'full' ? 200 : 0 }) }
</script>
<style scoped>
/* top:0 is BELOW the existing native navigation bar, not the status/capsule area. */
.motion-summary { position:fixed; top:0; left:0; right:0; z-index:800; height:var(--motion-summary-height); display:flex; align-items:center; gap:12px; padding:0 20px; background:#fdfefe; border-bottom:1px solid #e5eaf3; opacity:0; transform:translateY(-6px); pointer-events:none; transition:opacity var(--motion-summary) ease-out,transform var(--motion-summary) var(--motion-ease); }
.motion-summary--compact { opacity:1; transform:translateY(0); pointer-events:auto; }
.motion-summary__copy { display:flex; align-items:center; flex:1; min-width:0; gap:10px; }
.motion-summary__title { color:#203047; font-size:14px; font-weight:700; white-space:nowrap; }
.motion-summary__detail { min-width:0; overflow:hidden; text-overflow:ellipsis; white-space:nowrap; color:#66758b; font-size:12px; }
.motion-summary__top { margin:0; padding:8px 0 8px 8px; font-size:12px; line-height:1.3; color:#326be5; background:transparent; }
.motion-summary__top::after { border:0; }
.motion-summary__pressed { opacity:.7; }
</style>
