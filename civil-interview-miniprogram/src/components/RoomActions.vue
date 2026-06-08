<!--
这个小程序考场操作组件收拢录音、提交和下一题按钮，让考场主页面少背交互细节。

@param: 无；页面运行时从 props、路由参数、Pinia 状态和用户点击中拿数据。
@return: 渲染当前业务界面，并把按钮、表单或跳转事件交给既有流程处理。
@raises: 不主动抛业务异常；接口失败、未登录和权限不足由请求层或页面提示承接。
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
