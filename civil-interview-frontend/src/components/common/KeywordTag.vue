<template>
  <span class="keyword-tag" :class="[`keyword-tag--${type}`, { 'keyword-tag--missed': !matched }]">
    <span class="keyword-tag__word">{{ word }}</span>
    <span class="keyword-tag__value" v-if="displayValue">{{ displayValue }}</span>
  </span>
</template>

<script setup>
import { computed } from 'vue'

const props = defineProps({
  word: { type: String, required: true },
  type: { type: String, default: 'scoring' },
  value: { type: Number, default: 0 },
  matched: { type: Boolean, default: true }
})

const displayValue = computed(() => {
  if (!props.value) return ''
  if (props.type === 'deducting') return `${props.value}`
  return `+${props.value}`
})
</script>

<style lang="less" scoped>
@import '@/styles/variables.less';

.keyword-tag {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  padding: 2px 10px;
  border-radius: 12px;
  font-size: @font-size-sm;
  line-height: 20px;

  &--scoring {
    color: @score-green;
    background: fade(@score-green, 10%);
    border: 1px solid fade(@score-green, 25%);
  }
  &--deducting {
    color: @score-red;
    background: fade(@score-red, 10%);
    border: 1px solid fade(@score-red, 25%);
  }
  &--bonus {
    color: @score-gold;
    background: fade(@score-gold, 10%);
    border: 1px solid fade(@score-gold, 25%);
  }
  &--missed {
    opacity: 0.45;
    text-decoration: line-through;
  }
}

.keyword-tag__value {
  font-weight: 600;
  font-size: @font-size-xs;
}
</style>
