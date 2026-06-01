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
