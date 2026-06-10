<!--
错误边界组件，用来兜住局部渲染异常，避免单个组件失败拖垮整页。

@param: 通过 props、slot 和事件接收页面上下文；不直接拥有业务真源。
@return: 渲染可复用 UI，并通过 emit 或插槽把操作交还给父页面。
@raises: 不主动抛业务异常；异常状态应由父页面、请求层或兜底 UI 承接。
-->
<template>
  <div v-if="hasError" class="error-boundary">
    <div class="error-boundary__content">
      <div class="error-boundary__icon">⚠️</div>
      <h3 class="error-boundary__title">页面出现了问题</h3>
      <p class="error-boundary__msg">{{ errorMessage }}</p>
      <button class="error-boundary__btn" @click="reset">重新加载</button>
    </div>
  </div>
  <slot v-else />
</template>

<script setup>
import { ref, onErrorCaptured } from 'vue'
import { logger } from '@/utils/logger'

const hasError = ref(false)
const errorMessage = ref('')

onErrorCaptured((err) => {
  hasError.value = true
  errorMessage.value = err?.message || '未知错误'
  logger.error('Component error captured', {
    event: 'component.error_captured',
    error: err
  })
  return false // 阻止错误继续传播
})

function reset() {
  hasError.value = false
  errorMessage.value = ''
}
</script>

<style lang="less" scoped>
.error-boundary {
  display: flex;
  align-items: center;
  justify-content: center;
  min-height: 300px;
  padding: 32px 16px;
}

.error-boundary__content {
  text-align: center;
}

.error-boundary__icon {
  font-size: 48px;
  margin-bottom: 16px;
}

.error-boundary__title {
  font-size: 18px;
  color: #333;
  margin-bottom: 8px;
}

.error-boundary__msg {
  font-size: 14px;
  color: #999;
  margin-bottom: 20px;
}

.error-boundary__btn {
  padding: 8px 24px;
  border: 1px solid #1B5FAA;
  border-radius: 6px;
  background: #1B5FAA;
  color: #fff;
  font-size: 14px;
  cursor: pointer;
  transition: opacity 0.2s;

  &:hover {
    opacity: 0.85;
  }
}
</style>
