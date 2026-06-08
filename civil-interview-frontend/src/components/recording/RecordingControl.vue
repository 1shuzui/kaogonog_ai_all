<!--
这个录制控制组件统一开始、暂停、停止和状态提示，让专项和全真考场共用同一套按钮语义。

@param: 无；页面运行时从 props、路由参数、Pinia 状态和用户点击中拿数据。
@return: 渲染当前业务界面，并把按钮、表单或跳转事件交给既有流程处理。
@raises: 不主动抛业务异常；接口失败、未登录和权限不足由请求层或页面提示承接。
-->
<template>
  <div class="recording-control">
    <a-button
      v-if="status === 'idle'"
      type="primary"
      size="large"
      shape="round"
      @click="$emit('start-prep')"
    >
      <PlayCircleOutlined /> 开始准备
    </a-button>

    <a-button
      v-else-if="status === 'preparing'"
      type="primary"
      size="large"
      shape="round"
      :style="{ background: '#389E0D', borderColor: '#389E0D' }"
      @click="$emit('start-answer')"
    >
      <AudioOutlined /> 开始作答
    </a-button>

    <a-button
      v-else-if="status === 'answering'"
      type="primary"
      danger
      size="large"
      shape="round"
      @click="$emit('submit')"
    >
      <CheckCircleOutlined /> 提交答案
    </a-button>

    <a-button
      v-else-if="status === 'submitting'"
      size="large"
      shape="round"
      loading
      disabled
    >
      {{ submittingText }}
    </a-button>

    <div v-else-if="status === 'completed'" class="recording-control__done">
      <a-button
        v-if="!isLast"
        type="primary"
        size="large"
        shape="round"
        @click="$emit('next')"
      >
        <RightOutlined /> 下一题
      </a-button>
      <a-button
        type="primary"
        size="large"
        shape="round"
        :style="isLast ? {} : { background: '#389E0D', borderColor: '#389E0D' }"
        :loading="finishing"
        :disabled="finishing"
        @click="$emit('finish')"
      >
        <CheckOutlined /> {{ finishing ? finishingText : (isLast ? '查看结果' : '结束练习') }}
      </a-button>
    </div>
  </div>
</template>

<script setup>
import {
  PlayCircleOutlined,
  AudioOutlined,
  CheckCircleOutlined,
  RightOutlined,
  CheckOutlined
} from '@ant-design/icons-vue'

defineProps({
  status: { type: String, default: 'idle' },
  isLast: { type: Boolean, default: false },
  submittingText: { type: String, default: '处理中...' },
  finishing: { type: Boolean, default: false },
  finishingText: { type: String, default: '正在分析结果...' }
})

defineEmits(['start-prep', 'start-answer', 'submit', 'next', 'finish'])
</script>

<style lang="less" scoped>
.recording-control {
  display: flex;
  justify-content: center;

  .ant-btn-lg {
    min-width: 160px;
    height: 48px;
    font-size: 16px;
  }
}

.recording-control__done {
  display: flex;
  gap: 12px;
}
</style>
