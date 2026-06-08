<!--
这个省份选择组件复用在首页和资料设置里，避免省份名称、编码和默认值在页面之间不一致。

@param: 无；页面运行时从 props、路由参数、Pinia 状态和用户点击中拿数据。
@return: 渲染当前业务界面，并把按钮、表单或跳转事件交给既有流程处理。
@raises: 不主动抛业务异常；接口失败、未登录和权限不足由请求层或页面提示承接。
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
