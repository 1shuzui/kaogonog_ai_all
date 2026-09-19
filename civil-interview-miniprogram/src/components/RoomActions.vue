<!--
小程序考场操作栏组件，统一录音、重答、提交和按钮禁用状态。

@param: 通过 props、slot 和事件接收页面上下文；不直接拥有业务真源。
@return: 渲染可复用 UI，并通过 emit 或插槽把操作交还给父页面。
@raises: 不主动抛业务异常；异常状态应由父页面、请求层或兜底 UI 承接。
-->
<template>
  <view class="room-actions">
    <button class="secondary-button" :disabled="finishing || loading" @tap="$emit('exit')">{{ exitText }}</button>
    <button
      class="primary-button"
      :disabled="finishing || loading"
      :loading="loading || finishing"
      @tap="$emit('submit')"
    >
      {{ finishing || loading ? '正在整理录音' : isLastQuestion ? '提交并结束作答' : '提交并继续' }}
    </button>
  </view>
</template>

<script setup>
defineProps({
  finishing: { type: Boolean, default: false },
  loading: { type: Boolean, default: false },
  isLastQuestion: { type: Boolean, default: false },
  exitText: { type: String, default: '退出' },
})

defineEmits(['exit', 'submit'])
</script>

<style scoped>
/* Mini-program components do not inherit their parent's scoped selectors. */
.room-actions {
  display: grid;
  grid-template-columns: 180rpx minmax(0, 1fr);
  gap: 16rpx;
  padding: 20rpx 28rpx calc(20rpx + env(safe-area-inset-bottom));
  border-top: 1rpx solid #dbe3ee;
  background: #fdfefe;
}
.room-actions button {
  display: flex;
  align-items: center;
  justify-content: center;
  min-height: 88rpx;
  padding: 12rpx;
  border-radius: 24rpx;
  font-size: 28rpx;
  font-weight: 600;
}
.room-actions .primary-button { background: #326be5; color: #fff; }
.room-actions .secondary-button { background: #fdfefe; color: #285bc7; border: 1rpx solid #dbe3ee; }
</style>
