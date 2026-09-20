<template>
  <view class="motion-collapse" :style="theme">
    <view v-if="title" class="collapse-heading" @tap="$emit('toggle')" role="button" :aria-expanded="open">
      <text class="collapse-heading__title">{{ title }}</text>
      <view class="collapse-heading__actions" @tap.stop><slot name="actions" /></view>
      <view class="collapse-arrow" :class="{ 'collapse-arrow--open': open }"><text>⌄</text></view>
    </view>
    <view :id="shellId" class="collapse-shell" :class="animationClass" :style="shellStyle" @animationend="onEnd">
      <view v-if="state.mounted" class="collapse-content" :class="{ 'collapse-content--enter': state.phase === 'opening' && state.from <= .5 && state.duration > 0 }" :style="contentStyle"><slot /></view>
    </view>
  </view>
</template>
<script setup>
import { computed, getCurrentInstance, nextTick, onMounted, onBeforeUnmount, ref, watch } from 'vue'
import { createCollapse } from '../motion/collapse.mjs'
import { useMotion } from '../motion/useMotion'
import { motionStyle } from '../motion/policy.mjs'
import tokens from '../motion/tokens.json'
const props = defineProps({ open: Boolean, title: { type: String, default: '' }, revision: { default: null } })
const emit = defineEmits(['toggle', 'settled'])
const { proxy, uid } = getCurrentInstance()
const { mode, visible } = useMotion()
const state = ref({})
const shellId = `collapse-shell-${uid}`
const duration = () => mode.value === 'full' ? tokens.collapse : 0
const theme = computed(() => motionStyle(mode.value))
async function measure() {
  await nextTick() // node creation, not assumed to be a rendered animation frame
  return new Promise(resolve => {
    uni.createSelectorQuery().in(proxy).select('.collapse-shell').boundingClientRect()
      .select('.collapse-content').boundingClientRect().exec(result => {
        resolve(result?.[0] && result?.[1] ? { outer: result[0].height, inner: result[1].height } : null)
      })
  })
}
const collapse = createCollapse({ open: props.open, measure, publish: value => { state.value = value }, settled: () => emit('settled'), slack: tokens.settleSlack })
const animationClass = computed(() => ['opening', 'closing'].includes(state.value.phase) && state.value.duration > 0 ? (state.value.animation % 2 ? 'collapse-shell--a' : 'collapse-shell--b') : '')
const shellStyle = computed(() => {
  const item = state.value
  return {
    height: item.height, overflow: item.phase === 'open' ? 'visible' : 'hidden',
    animationDuration: `${item.duration}ms`, animationTimingFunction: tokens.easing, animationFillMode: 'both',
    animationPlayState: visible.value ? 'running' : 'paused',
    '--collapse-from': `${item.from}px`, '--collapse-to': `${item.to}px`,
    pointerEvents: item.interactive ? 'auto' : 'none'
  }
})
const contentStyle = computed(() => ({ opacity: props.open ? 1 : 0, transform: `translateY(${props.open || mode.value !== 'full' ? 0 : -4}px)`, transitionDuration: `${mode.value === 'full' ? (props.open ? tokens.enter : tokens.exit) : 0}ms` }))
function onEnd(event) {
  if (event.target?.id !== shellId || event.currentTarget?.id !== shellId) return
  collapse.complete(state.value.id)
}
const remeasure = () => collapse.resize(duration())
watch(() => props.open, value => collapse.set(value, duration()))
watch(() => props.revision, remeasure, { deep: true, flush: 'sync' })
watch(mode, () => collapse.set(props.open, duration()))
watch(visible, value => value ? collapse.resume(duration()) : collapse.pause())
onMounted(() => { if (visible.value) collapse.set(props.open, 0); else collapse.pause(); uni.onWindowResize?.(remeasure) })
onBeforeUnmount(() => { collapse.dispose(); uni.offWindowResize?.(remeasure) })
defineExpose({ remeasure })
</script>
<style scoped>
.motion-collapse { display:block; }
.collapse-heading { display:flex; align-items:center; gap:9px; min-height:44px; margin-top:18px; padding:0 2px; color:#203047; }
.collapse-heading__title { flex:1; font-size:30rpx; font-weight:700; }
.collapse-heading__actions { display:flex; align-items:center; }
.collapse-arrow { display:flex; justify-content:center; align-items:center; width:24px; height:24px; background:#eaf5ff; color:#326be5; border-radius:50%; transform:rotate(0); transition:transform var(--motion-arrow) var(--motion-ease); }
.collapse-arrow--open { transform:rotate(180deg); }
.collapse-arrow text { font-size:14px; font-weight:700; }
.collapse-shell { min-height:0; }
.collapse-shell--a { animation-name:collapse-height-a; }
.collapse-shell--b { animation-name:collapse-height-b; }
.collapse-content { display:flex; flex-direction:column; min-height:0; transition-property:opacity,transform; transition-timing-function:ease-out; }
.collapse-content--enter { animation:collapse-content-in var(--motion-enter) var(--motion-ease) both; }
@keyframes collapse-content-in { from { opacity:0; transform:translateY(4px); } to { opacity:1; transform:translateY(0); } }
@keyframes collapse-height-a { from { height:var(--collapse-from); } to { height:var(--collapse-to); } }
@keyframes collapse-height-b { from { height:var(--collapse-from); } to { height:var(--collapse-to); } }
</style>
