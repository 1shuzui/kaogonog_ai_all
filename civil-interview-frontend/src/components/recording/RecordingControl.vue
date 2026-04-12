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
      评分中...
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
        v-else
        type="primary"
        size="large"
        shape="round"
        @click="$emit('finish')"
      >
        <CheckOutlined /> 查看结果
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
  isLast: { type: Boolean, default: false }
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
