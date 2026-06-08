<!--
这个小程序统计宫格展示次数、时长和分数等摘要，首页和我的页面能复用同一套信息密度。

@param: 无；页面运行时从 props、路由参数、Pinia 状态和用户点击中拿数据。
@return: 渲染当前业务界面，并把按钮、表单或跳转事件交给既有流程处理。
@raises: 不主动抛业务异常；接口失败、未登录和权限不足由请求层或页面提示承接。
-->
<template>
  <view class="stat-grid">
    <view v-for="item in items" :key="item.label" class="stat-grid__item">
      <text class="stat-grid__value">{{ item.value }}</text>
      <text class="stat-grid__label">{{ item.label }}</text>
    </view>
  </view>
</template>

<script setup>
defineProps({
  items: {
    type: Array,
    default: () => []
  }
})
</script>

<style scoped>
.stat-grid {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 16rpx;
  margin-bottom: 20rpx;
}

.stat-grid__item {
  min-height: 120rpx;
  padding: 22rpx 12rpx;
  border: 1rpx solid rgba(27, 95, 170, 0.08);
  border-radius: 16rpx;
  background: #ffffff;
  text-align: center;
  box-shadow: 0 6rpx 18rpx rgba(23, 48, 78, 0.05);
}

.stat-grid__value {
  display: block;
  color: #1b5faa;
  font-size: 36rpx;
  font-weight: 800;
  line-height: 1.2;
}

.stat-grid__label {
  display: block;
  margin-top: 8rpx;
  color: #6f7c8f;
  font-size: 23rpx;
}
</style>
