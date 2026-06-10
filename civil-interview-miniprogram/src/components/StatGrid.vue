<!--
小程序数据宫格组件，用于首页和我的页展示统计摘要。

@param: 通过 props、slot 和事件接收页面上下文；不直接拥有业务真源。
@return: 渲染可复用 UI，并通过 emit 或插槽把操作交还给父页面。
@raises: 不主动抛业务异常；异常状态应由父页面、请求层或兜底 UI 承接。
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
  border: 1rpx solid #DCEAF7;
  border-radius: 16rpx;
  background: #ffffff;
  text-align: center;
  box-shadow: 0 6rpx 18rpx rgba(47, 127, 214, 0.04);
}

.stat-grid__value {
  display: block;
  color: #2F7FD6;
  font-size: 36rpx;
  font-weight: 800;
  line-height: 1.2;
}

.stat-grid__label {
  display: block;
  margin-top: 8rpx;
  color: #64748B;
  font-size: 23rpx;
}
</style>
