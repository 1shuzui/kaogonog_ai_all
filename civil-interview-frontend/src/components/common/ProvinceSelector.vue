<template>
  <a-select
    v-model:value="selected"
    :options="options"
    placeholder="选择省份"
    style="min-width: 120px"
    @change="onSelect"
  />
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { useUserStore } from '@/stores/user'

const emit = defineEmits(['change'])
const userStore = useUserStore()

const selected = ref(userStore.selectedProvince)

const options = computed(() =>
  [{ value: 'all', label: '全部省份' }, ...userStore.provinces.map(p => ({ value: p.code, label: p.name }))]
)

onMounted(() => {
  if (!userStore.provinces.length) {
    userStore.loadProvinces()
  }
})

function onSelect(value) {
  emit('change', value)
}
</script>
