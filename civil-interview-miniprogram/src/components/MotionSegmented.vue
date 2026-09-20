<template>
  <view class="motion-segmented" :style="style" aria-role="tablist">
    <view class="motion-segmented__rail">
      <view v-if="selected >= 0" class="motion-segmented__plate" :style="{ width: `${100 / options.length}%`, transform: `translateX(${selected * 100}%)` }" />
      <button v-for="item in options" :key="item.value" class="motion-segmented__item"
        :class="{ 'motion-segmented__item--selected': item.value === modelValue }"
        :disabled="disabled || item.disabled" :aria-selected="item.value === modelValue"
        hover-class="motion-segmented__pressed" @tap="select(item)">
        <text>{{ item.label }}</text><text v-if="item.count != null" class="motion-segmented__count">{{ item.count }}</text>
      </button>
    </view>
  </view>
</template>
<script setup>
import { computed } from 'vue'
import { useMotion } from '../motion/useMotion'
import { motionStyle } from '../motion/policy.mjs'
const props = defineProps({ modelValue: { type: [String, Number], default: '' }, options: { type: Array, default: () => [] }, disabled: Boolean })
const emit = defineEmits(['update:modelValue', 'change'])
const { mode } = useMotion()
const selected = computed(() => props.options.findIndex(item => item.value === props.modelValue))
const style = computed(() => motionStyle(mode.value))
function select(item) {
  if (props.disabled || item.disabled || item.value === props.modelValue) return
  emit('update:modelValue', item.value)
  emit('change', item.value)
}
</script>
<style scoped>
.motion-segmented { padding:4px; margin:12px 0 16px; border:1px solid #e5eaf3; border-radius:16px; background:#eef2f8; }
.motion-segmented__rail { position:relative; display:flex; }
.motion-segmented__plate { position:absolute; top:0; bottom:0; left:0; border-radius:12px; background:#fdfefe; box-shadow:0 2px 5px rgba(32,48,71,.07); transition:transform var(--motion-segment) var(--motion-ease); pointer-events:none; }
.motion-segmented__item { position:relative; flex:1; display:flex; justify-content:center; align-items:center; gap:4px; min-width:0; min-height:44px; margin:0; padding:8px 2px; background:transparent; color:var(--ui-muted, #596a80); border-radius:12px; font-size:14px; line-height:1.4; transition:transform var(--motion-press) ease-out,opacity var(--motion-press) ease-out; }
.motion-segmented__item::after { border:0; }
.motion-segmented__item--selected { color:var(--ui-link, #285bc7); font-weight:700; }
.motion-segmented__count { font-size:12px; }
.motion-segmented__pressed { transform:scale(var(--motion-scale)); opacity:.75; }
</style>
