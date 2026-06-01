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
        <h2>请先设置考试偏好</h2>
        <p>
          后续的随机抽题、定向备面、题库筛选会优先按所选地区、考试大类和题型展示；
          不选时系统会随机练习，也可以在"考试设置"中随时修改。
        </p>
      </div>

      <div class="province-gate__section-title">备考地区</div>
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

      <div class="province-gate__section-title">考试大类</div>
      <div class="province-gate__grid">
        <button
          v-for="cat in examCategoryOptions"
          :key="cat.id"
          type="button"
          class="province-gate__chip"
          :class="{ 'is-active': selectedExamCategory === cat.name }"
          @click="selectedExamCategory = selectedExamCategory === cat.name ? '' : cat.name"
        >
          {{ cat.name }}
        </button>
      </div>

      <div class="province-gate__section-title">注重题型</div>
      <div class="province-gate__type-grid">
        <button
          v-for="item in preferredQuestionOptions"
          :key="item.key"
          type="button"
          class="province-gate__chip"
          :class="{ 'is-active': selectedDimensions.includes(item.key) }"
          @click="toggleDimension(item.key)"
        >
          {{ item.name }}
        </button>
      </div>

      <div class="province-gate__footer">
        <span class="province-gate__hint">题型可暂不选择，留空代表随机</span>
        <a-button type="primary" size="large" :loading="saving" :disabled="!selectedProvince || saving" @click="confirmProvince">
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
import { QUESTION_CATEGORIES, PROVINCES } from '@/utils/constants'
import { DEFAULT_TARGETED_POSITION_TREE } from '@/utils/targetedOptions'

const props = defineProps({
  open: {
    type: Boolean,
    default: false
  }
})

const emit = defineEmits(['confirmed'])
const userStore = useUserStore()
const saving = ref(false)

function isExplicitProvince(code = '') {
  const normalized = String(code || '').trim()
  return !!normalized && normalized !== 'national'
}

const options = computed(() => {
  const source = userStore.provinces.length ? userStore.provinces : PROVINCES
  return source.filter((item) => isExplicitProvince(item?.code))
})

const selectedProvince = ref(
  userStore.hasConfirmedProvinceSelection && isExplicitProvince(userStore.selectedProvince)
    ? userStore.selectedProvince
    : ''
)
const selectedDimensions = ref([])
const selectedExamCategory = ref('')
const examCategoryOptions = computed(() =>
  DEFAULT_TARGETED_POSITION_TREE.map(cat => ({ id: cat.id, name: cat.name }))
)
const preferredQuestionOptions = computed(() => QUESTION_CATEGORIES.filter((item) => item.key))

watch(
  () => props.open,
  (value) => {
    if (value) {
      selectedProvince.value = userStore.hasConfirmedProvinceSelection && isExplicitProvince(userStore.selectedProvince)
        ? userStore.selectedProvince
        : ''
      selectedDimensions.value = Array.isArray(userStore.preferences?.preferredQuestionDimensions)
        ? [...userStore.preferences.preferredQuestionDimensions]
        : []
      selectedExamCategory.value = userStore.preferences?.examCategory || ''
    }
  }
)

function toggleDimension(key) {
  if (!key) return
  if (selectedDimensions.value.includes(key)) {
    selectedDimensions.value = selectedDimensions.value.filter((item) => item !== key)
    return
  }
  selectedDimensions.value = [...selectedDimensions.value, key]
}

async function confirmProvince() {
  if (!isExplicitProvince(selectedProvince.value) || saving.value) return
  saving.value = true
  try {
    const result = await userStore.confirmProvinceSelection(selectedProvince.value)
    if (result?.success === false) {
      message.error('偏好保存失败，请稍后重试')
      return
    }
    await userStore.savePreferences({
      ...userStore.preferences,
      preferredQuestionDimensions: selectedDimensions.value,
      practicePreferenceConfirmed: true,
      examCategory: selectedExamCategory.value
    })
    emit('confirmed', selectedProvince.value)
  } finally {
    saving.value = false
  }
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

.province-gate__section-title {
  color: @text-primary;
  font-size: @font-size-base;
  font-weight: 700;
}

.province-gate__type-grid {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
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

  .province-gate__type-grid {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }

  .province-gate__footer {
    flex-direction: column;
    align-items: stretch;
  }
}
</style>
