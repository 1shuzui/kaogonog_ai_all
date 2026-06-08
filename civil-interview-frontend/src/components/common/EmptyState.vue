<!--
这个空状态组件用于无历史、无题目、无分析结果等场景，统一空态文案和按钮位置，减少页面显得像报错。

@param: 无；页面运行时从 props、路由参数、Pinia 状态和用户点击中拿数据。
@return: 渲染当前业务界面，并把按钮、表单或跳转事件交给既有流程处理。
@raises: 不主动抛业务异常；接口失败、未登录和权限不足由请求层或页面提示承接。
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
