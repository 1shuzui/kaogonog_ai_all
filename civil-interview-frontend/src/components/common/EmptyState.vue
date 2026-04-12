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
