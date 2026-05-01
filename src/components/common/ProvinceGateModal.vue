<template>
  <a-modal
    :open="open"
    :closable="false"
    :maskClosable="false"
    :keyboard="false"
    centered
    width="720px"
    :footer="null"
  >
    <div class="province-gate">
      <div class="province-gate__header">
        <span class="province-gate__eyebrow">首次进入设置</span>
        <h2>请先选择你的备考省份</h2>
        <p>
          后续的随机抽题、定向备面、题库筛选都会优先按这个省份展示，
          你也可以在右上角或个人中心随时修改。
        </p>
      </div>

      <div class="province-gate__grid">
        <button
          v-for="item in options"
          :key="item.code"
          type="button"
          class="province-gate__chip"
          :class="{ 'is-active': selectedProvince === item.code }"
          @click="selectedProvince = item.code"
        >
          {{ item.name }}
        </button>
      </div>

      <div class="province-gate__footer">
        <span class="province-gate__hint">建议按你当前主要备考地区选择</span>
        <a-button type="primary" size="large" :disabled="!selectedProvince" @click="confirmProvince">
          确认并进入
        </a-button>
      </div>
    </div>
  </a-modal>
</template>

<script setup>
import { computed, ref, watch } from 'vue'
import { message } from 'ant-design-vue'
import { useUserStore } from '@/stores/user'
import { PROVINCES } from '@/utils/constants'

const props = defineProps({
  open: {
    type: Boolean,
    default: false
  }
})

const emit = defineEmits(['confirmed'])
const userStore = useUserStore()

const options = computed(() => {
  if (userStore.provinces.length) return userStore.provinces
  return PROVINCES
})

const selectedProvince = ref(userStore.selectedProvince || '')

watch(
  () => props.open,
  (value) => {
    if (value) {
      selectedProvince.value = userStore.selectedProvince || ''
    }
  }
)

async function confirmProvince() {
  if (!selectedProvince.value) return
  const result = await userStore.confirmProvinceSelection(selectedProvince.value)
  if (result?.success === false) {
    message.error('省份保存失败，请稍后重试')
    return
  }
  emit('confirmed', selectedProvince.value)
}
</script>

<style lang="less" scoped>
@import '@/styles/variables.less';

.province-gate {
  display: flex;
  flex-direction: column;
  gap: 20px;
}

.province-gate__header h2 {
  margin: 8px 0 10px;
  color: @text-primary;
  font-size: 30px;
}

.province-gate__header p {
  margin: 0;
  color: @text-secondary;
  line-height: 1.8;
}

.province-gate__eyebrow {
  display: inline-flex;
  align-items: center;
  min-height: 28px;
  padding: 0 12px;
  border-radius: 999px;
  background: rgba(27, 95, 170, 0.08);
  color: @primary-color;
  font-size: 12px;
  font-weight: 600;
}

.province-gate__grid {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 10px;
}

.province-gate__chip {
  min-height: 46px;
  padding: 0 12px;
  border-radius: 16px;
  border: 1px solid rgba(27, 95, 170, 0.12);
  background: #fff;
  color: @text-regular;
  font-size: @font-size-sm;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.2s ease;
}

.province-gate__chip:hover,
.province-gate__chip.is-active {
  border-color: rgba(27, 95, 170, 0.42);
  background: linear-gradient(135deg, rgba(27, 95, 170, 0.12) 0%, rgba(95, 160, 232, 0.12) 100%);
  color: @primary-color;
  box-shadow: 0 12px 24px rgba(27, 95, 170, 0.12);
}

.province-gate__footer {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 12px;
}

.province-gate__hint {
  color: @text-secondary;
  font-size: @font-size-sm;
}

@media (max-width: 768px) {
  .province-gate__grid {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }

  .province-gate__footer {
    flex-direction: column;
    align-items: stretch;
  }
}
</style>
