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
  background: #e8f4fd;
  color: #1b5faa;
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
  color: #6f7c8f;
  font-size: 24rpx;
  line-height: 1.6;
}
</style>
