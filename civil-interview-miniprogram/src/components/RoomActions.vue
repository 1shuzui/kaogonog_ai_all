<!--
小程序考场操作栏组件，统一录音、重答、提交和按钮禁用状态。

@param: 通过 props、slot 和事件接收页面上下文；不直接拥有业务真源。
@return: 渲染可复用 UI，并通过 emit 或插槽把操作交还给父页面。
@raises: 不主动抛业务异常；异常状态应由父页面、请求层或兜底 UI 承接。
-->
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
