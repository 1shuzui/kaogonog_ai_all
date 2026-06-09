<!--
这个组件替代系统 picker 的黑底弹窗；定向备面、题库筛选等选择器用它保持浅色主题和一致交互。

@param: 无；页面运行时从 props、路由参数、Pinia 状态和用户点击中拿数据。
@return: 渲染当前业务界面，并把按钮、表单或跳转事件交给既有流程处理。
@raises: 不主动抛业务异常；接口失败、未登录和权限不足由请求层或页面提示承接。
-->
<template>
  <view>
    <view @tap="open">
      <slot />
    </view>
    <view v-if="visible" class="selector-overlay" @tap="close">
      <view class="selector-panel" @tap.stop>
        <view class="selector-head">
          <text class="selector-title">{{ title }}</text>
          <text class="selector-done" @tap="close">完成</text>
        </view>
        <scroll-view scroll-y class="selector-list">
          <view
            v-for="(item, index) in normalizedOptions"
            :key="`${item.value}-${index}`"
            class="selector-option"
            :class="{ 'selector-option--active': index === activeIndex }"
            @tap="choose(index)"
          >
            <text>{{ item.label }}</text>
            <text v-if="index === activeIndex" class="selector-check">✓</text>
          </view>
        </scroll-view>
      </view>
    </view>
  </view>
</template>

<script setup>
import { computed, ref } from 'vue'

const props = defineProps({
  title: { type: String, default: '请选择' },
  options: { type: Array, default: () => [] },
  value: { type: Number, default: 0 },
  disabled: { type: Boolean, default: false }
})

const emit = defineEmits(['change'])
const visible = ref(false)
const normalizedOptions = computed(() => props.options.map((item, index) => {
  if (typeof item === 'string') return { label: item, value: index }
  return {
    label: String(item?.label ?? item?.name ?? item?.text ?? ''),
    value: item?.value ?? index
  }
}).filter((item) => item.label))
const activeIndex = computed(() => {
  if (!normalizedOptions.value.length) return -1
  const index = Number(props.value || 0)
  return index >= 0 && index < normalizedOptions.value.length ? index : 0
})

function open() {
  if (props.disabled || !normalizedOptions.value.length) return
  visible.value = true
}

function close() {
  visible.value = false
}

function choose(index) {
  emit('change', { detail: { value: index } })
  close()
}
</script>

<style scoped>
.selector-overlay {
  position: fixed;
  top: 0;
  right: 0;
  bottom: 0;
  left: 0;
  z-index: 2200;
  display: flex;
  align-items: flex-end;
  justify-content: center;
  background: rgba(15, 23, 42, 0.42);
  animation: selector-mask-in 180ms ease-out both;
}

.selector-panel {
  width: 100%;
  max-height: 68vh;
  padding: 24rpx 28rpx calc(24rpx + env(safe-area-inset-bottom));
  border-radius: 24rpx 24rpx 0 0;
  background: #ffffff;
  color: #172033;
  box-shadow: 0 -12rpx 36rpx rgba(47, 127, 214, 0.10);
  animation: selector-sheet-up 220ms ease-out both;
}

.selector-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 16rpx;
}

.selector-title {
  color: #172033;
  font-size: 30rpx;
  font-weight: 700;
}

.selector-done {
  color: #2F7FD6;
  font-size: 26rpx;
  font-weight: 600;
}

.selector-list {
  max-height: 54vh;
}

.selector-option {
  display: flex;
  align-items: center;
  justify-content: space-between;
  min-height: 88rpx;
  padding: 0 6rpx;
  border-bottom: 1rpx solid #eef2f6;
  color: #2a3648;
  font-size: 28rpx;
  transition: transform 160ms ease, background-color 160ms ease, color 160ms ease;
}

.selector-option:last-child {
  border-bottom: 0;
}

.selector-option--active {
  padding: 0 16rpx;
  border-radius: 12rpx;
  background: #EAF5FF;
  color: #2F7FD6;
  font-weight: 700;
  transform: translateX(4rpx);
}

.selector-check {
  color: #2F7FD6;
  font-size: 28rpx;
  animation: selector-check-pop 180ms ease-out both;
}

@keyframes selector-mask-in {
  from {
    opacity: 0;
  }
  to {
    opacity: 1;
  }
}

@keyframes selector-sheet-up {
  from {
    opacity: 0;
    transform: translate3d(0, 44rpx, 0);
  }
  to {
    opacity: 1;
    transform: translate3d(0, 0, 0);
  }
}

@keyframes selector-check-pop {
  from {
    opacity: 0;
    transform: scale(0.72);
  }
  to {
    opacity: 1;
    transform: scale(1);
  }
}
</style>
