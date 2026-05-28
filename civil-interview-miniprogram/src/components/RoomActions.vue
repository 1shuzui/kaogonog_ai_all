<template>
  <view class="room-actions">
    <button class="secondary-button" @tap="$emit('exit')">退出</button>
    <button
      class="primary-button"
      :disabled="finishing"
      :loading="loading || finishing"
      @tap="$emit('submit')"
    >
      {{ finishing ? '正在分析结果...' : isLastQuestion ? '提交并看结果' : '提交本题' }}
    </button>
  </view>
</template>

<script setup>
defineProps({
  finishing: { type: Boolean, default: false },
  loading: { type: Boolean, default: false },
  isLastQuestion: { type: Boolean, default: false },
})

defineEmits(['exit', 'submit'])
</script>
