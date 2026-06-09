<!--
这个空状态组件用于无历史、无题目、无分析结果等场景，统一空态文案和按钮位置，减少页面显得像报错。

@param: 无；页面运行时从 props、路由参数、Pinia 状态和用户点击中拿数据。
@return: 渲染当前业务界面，并把按钮、表单或跳转事件交给既有流程处理。
@raises: 不主动抛业务异常；接口失败、未登录和权限不足由请求层或页面提示承接。
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
