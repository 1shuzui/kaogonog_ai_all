<!--
空状态组件，用统一文案承接无数据、无权限和加载失败，避免页面出现突兀空白。

@param: 通过 props、slot 和事件接收页面上下文；不直接拥有业务真源。
@return: 渲染可复用 UI，并通过 emit 或插槽把操作交还给父页面。
@raises: 不主动抛业务异常；异常状态应由父页面、请求层或兜底 UI 承接。
-->
<template>
  <div class="empty-state">
    <InboxOutlined class="empty-state__icon" />
    <p class="empty-state__text">{{ text }}</p>
    <div v-if="$slots.action" class="empty-state__action">
      <slot name="action" />
    </div>
    <slot />
  </div>
</template>

<script setup>
import { InboxOutlined } from '@ant-design/icons-vue'

defineProps({
  text: { type: String, default: '暂无数据' }
})
</script>

<style lang="less" scoped>
@import '@/styles/variables.less';

.empty-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 48px 16px;
  color: @text-secondary;
}

.empty-state__icon {
  font-size: 48px;
  color: #d9d9d9;
  margin-bottom: 12px;
}

.empty-state__text {
  font-size: @font-size-base;
}

.empty-state__action {
  margin-top: 12px;
}
</style>
