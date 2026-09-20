<!--
小程序浅色选择器组件，替代系统 picker 的黑底弹窗，保证定向和筛选体验一致。

@param: 通过 props、slot 和事件接收页面上下文；不直接拥有业务真源。
@return: 渲染可复用 UI，并通过 emit 或插槽把操作交还给父页面。
@raises: 不主动抛业务异常；异常状态应由父页面、请求层或兜底 UI 承接。
-->
<template>
  <view>
    <view @tap="open">
      <slot />
    </view>
    <LearnerSheet class="selector-sheet" :show="visible" :title="title" :body-height="normalizedOptions.length * 56" @close="close">
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
    </LearnerSheet>
  </view>
</template>

<script setup>
import LearnerSheet from './LearnerSheet.vue'
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
.selector-option {
  display: flex;
  align-items: center;
  justify-content: space-between;
  min-height: 48px;
  padding: 12px 6px;
  gap: 12px;
  border-bottom: 1rpx solid #eef2f6;
  color: #2a3648;
  font-size: 15px;
  line-height: 1.6;
  transition: background-color var(--motion-press) ease;
}

.selector-option:last-child {
  border-bottom: 0;
}

.selector-option--active {
  padding: 12px 12px;
  border-radius: 12rpx;
  background: var(--ui-soft, #edf3ff);
  color: var(--ui-link, #285bc7);
  font-weight: 700;
}

.selector-check {
  color: var(--ui-link, #285bc7);
  font-size: 28rpx;
}

</style>
