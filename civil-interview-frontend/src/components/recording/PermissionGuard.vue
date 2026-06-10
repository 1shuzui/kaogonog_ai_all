<!--
录音权限提示组件，用于在作答前说明麦克风权限，避免提交后才发现无音频。

@param: 通过 props、slot 和事件接收页面上下文；不直接拥有业务真源。
@return: 渲染可复用 UI，并通过 emit 或插槽把操作交还给父页面。
@raises: 不主动抛业务异常；异常状态应由父页面、请求层或兜底 UI 承接。
-->
<template>
  <div class="permission-guard" v-if="!allReady">
    <div class="permission-guard__content">
      <ExclamationCircleOutlined class="permission-guard__icon" />
      <h3>需要设备权限</h3>
      <p>本测评需要使用摄像头和麦克风录制您的作答过程</p>
      <a-button type="primary" :loading="checking" @click="requestPermissions">
        授权使用设备
      </a-button>
      <p class="permission-guard__error" v-if="error">{{ error }}</p>
    </div>
  </div>
  <slot v-else />
</template>

<script setup>
import { computed } from 'vue'
import { ExclamationCircleOutlined } from '@ant-design/icons-vue'

const props = defineProps({
  cameraReady: { type: Boolean, default: false },
  micReady: { type: Boolean, default: false },
  checking: { type: Boolean, default: false },
  error: { type: String, default: '' }
})

const emit = defineEmits(['request'])

const allReady = computed(() => props.cameraReady && props.micReady)

function requestPermissions() {
  emit('request')
}
</script>

<style lang="less" scoped>
@import '@/styles/variables.less';

.permission-guard {
  display: flex;
  align-items: center;
  justify-content: center;
  min-height: 300px;
  padding: 32px;
}

.permission-guard__content {
  text-align: center;

  h3 {
    margin: 16px 0 8px;
    font-size: @font-size-lg;
    color: @text-primary;
  }
  p {
    color: @text-secondary;
    margin-bottom: 20px;
    font-size: @font-size-sm;
  }
}

.permission-guard__icon {
  font-size: 48px;
  color: @primary-color;
}

.permission-guard__error {
  color: @score-red !important;
  margin-top: 12px;
}
</style>
