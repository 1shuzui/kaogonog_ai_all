<!-- Shared learner sheet. Only the visual layer is portalled; Vue retains state ownership. -->
<template>
  <!-- #ifdef MP-WEIXIN -->
  <root-portal>
  <!-- #endif -->
  <!-- #ifdef H5 -->
  <teleport to="body">
  <!-- #endif -->
    <MotionPresence :show="show && visible" layer>
      <view class="learner-sheet" :style="theme">
        <view class="sheet-backdrop" @tap="close" @touchmove.stop.prevent="noop" />
        <view class="sheet-panel" role="dialog" :aria-label="title" @tap.stop @touchmove.stop.prevent="noop">
          <view class="sheet-heading">
            <text class="sheet-title">{{ title }}</text>
            <button class="sheet-close" hover-class="sheet-close--pressed" @tap="close">{{ closeLabel }}</button>
          </view>
          <scroll-view class="sheet-scroll" scroll-y :bounces="false" enhanced :show-scrollbar="true" :style="scrollStyle">
            <view class="sheet-content"><slot /></view>
          </scroll-view>
        </view>
      </view>
    </MotionPresence>
  <!-- #ifdef H5 -->
  </teleport>
  <!-- #endif -->
  <!-- #ifdef MP-WEIXIN -->
  </root-portal>
  <!-- #endif -->
</template>

<script setup>
import { computed, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import MotionPresence from './MotionPresence.vue'
import { useMotion } from '../motion/useMotion'
import { motionStyle } from '../motion/policy.mjs'

const props = defineProps({
  show: Boolean,
  title: { type: String, default: '请选择' },
  closeLabel: { type: String, default: '完成' },
  bodyHeight: { type: Number, default: 320 }
})
const emit = defineEmits(['close'])
const { mode, visible } = useMotion()
const windowHeight = ref(640)
const theme = computed(() => motionStyle(mode.value))
const scrollStyle = computed(() => ({ height: `${Math.min(Math.max(88, props.bodyHeight), windowHeight.value * .58)}px` }))
function resize() {
  try { windowHeight.value = (uni.getWindowInfo ? uni.getWindowInfo() : uni.getSystemInfoSync()).windowHeight || 640 } catch {}
}
function close() { emit('close') }
function noop() {}
// A cached tab must not reopen a stale mask when revisited.
watch(visible, active => { if (!active && props.show) close() })
watch(() => props.show, value => { if (value) { resize(); uni.hideKeyboard?.() } })
onMounted(() => { resize(); uni.onWindowResize?.(resize) })
onBeforeUnmount(() => uni.offWindowResize?.(resize))
</script>

<style scoped>
.learner-sheet { position:fixed; top:0; right:0; bottom:0; left:0; color:var(--ui-text, #203047); font-family:"PingFang SC","Microsoft YaHei",sans-serif; }
.sheet-backdrop { position:absolute; top:0; right:0; bottom:0; left:0; background:rgba(20,36,58,.38); }
.sheet-panel { position:absolute; bottom:0; left:0; right:0; padding:12px 20px calc(16px + env(safe-area-inset-bottom)); background:var(--ui-surface, #fdfefe); border-radius:24px 24px 0 0; box-shadow:0 -6px 28px #20304714; }
.sheet-heading { display:flex; align-items:center; justify-content:space-between; gap:12px; min-height:52px; margin-bottom:8px; }
.sheet-title { font-size:18px; font-weight:700; line-height:1.5; }
.sheet-close { display:flex; align-items:center; justify-content:center; flex-shrink:0; min-width:60px; min-height:44px; padding:8px 12px; color:var(--ui-link, #285bc7); background:var(--ui-soft, #edf3ff); border-radius:12px; font-size:15px; font-weight:600; }
.sheet-close--pressed { opacity:.8; }
.sheet-content { padding-bottom:4px; }
</style>
