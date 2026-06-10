<!--
省份选择组件，统一地区入口展示，避免页面手写省份列表。

@param: 通过 props、slot 和事件接收页面上下文；不直接拥有业务真源。
@return: 渲染可复用 UI，并通过 emit 或插槽把操作交还给父页面。
@raises: 不主动抛业务异常；异常状态应由父页面、请求层或兜底 UI 承接。
-->
<template>
  <a-select
    :value="selected"
    :options="options"
    placeholder="选择地区"
    style="min-width: 120px"
    @change="onSelect"
  />
</template>

<script setup>
import { computed, onMounted } from 'vue'
import { useUserStore } from '@/stores/user'

const props = defineProps({
  value: { type: String, default: undefined }
})
const emit = defineEmits(['change', 'update:value'])
const userStore = useUserStore()

const selected = computed(() => props.value ?? userStore.selectedProvince)

const options = computed(() =>
  [{ value: 'all', label: '全部地区' }, ...userStore.provinces.map(p => ({ value: p.code, label: p.name }))]
)

onMounted(() => {
  if (!userStore.provinces.length) {
    userStore.loadProvinces()
  }
})

function onSelect(value) {
  emit('update:value', value)
  emit('change', value)
}
</script>
