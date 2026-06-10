<!--
空状态组件，用统一文案承接无数据、无权限和加载失败，避免页面出现突兀空白。

@param: 通过 props、slot 和事件接收页面上下文；不直接拥有业务真源。
@return: 渲染可复用 UI，并通过 emit 或插槽把操作交还给父页面。
@raises: 不主动抛业务异常；异常状态应由父页面、请求层或兜底 UI 承接。
-->
<template>
  <view class="empty">
    <view class="empty__mark">{{ mark }}</view>
    <text class="empty__title">{{ title }}</text>
    <text v-if="desc" class="empty__desc">{{ desc }}</text>
    <slot />
  </view>
</template>

<script setup>
defineProps({
  title: {
    type: String,
    default: '暂无数据'
  },
  desc: {
    type: String,
    default: ''
  },
  mark: {
    type: String,
    default: '—'
  }
})
</script>

<style scoped>
.empty {
  display: flex;
  align-items: center;
  flex-direction: column;
  justify-content: center;
  min-height: 300rpx;
  padding: 42rpx 24rpx;
  text-align: center;
}

.empty__mark {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 88rpx;
  height: 88rpx;
  margin-bottom: 18rpx;
  border-radius: 999rpx;
  background: #EAF5FF;
  color: #2F7FD6;
  font-size: 42rpx;
  font-weight: 700;
}

.empty__title {
  color: #2a3648;
  font-size: 30rpx;
  font-weight: 600;
}

.empty__desc {
  margin-top: 8rpx;
  color: #64748B;
  font-size: 24rpx;
  line-height: 1.6;
}
</style>
