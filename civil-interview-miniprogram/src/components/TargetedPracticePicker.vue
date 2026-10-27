<template>
  <view class="card targeted-picker">
    <text class="section-title">{{ config.questionType }} · 针对练习</text>
    <text class="page-desc">{{ scopeLabel }}</text>
    <template v-if="!fixedIds.length">
      <MotionSegmented :model-value="config.mode" :options="modes" @change="changeMode" />
      <view class="count-options"><text>本轮题量</text><button v-for="size in [1, 3, 5]" :key="size" class="count-option" :class="{ selected: config.count === size }" :disabled="disabled" @tap="changeCount(size)">{{ size }} 题</button></view>
    </template>
    <text v-else class="page-desc">重练所选原题，保留原题目。</text>
    <text class="picker-note">{{ config.mode === 'new' ? '仅选择同方向、同题型中尚未实际作答的题目。' : config.mode === 'low_score' ? '使用当前分析期和独立分析低分标准，与错题本个人低分线无关。' : '仅复练同方向、同题型的已做题目。' }}</text>
    <text v-if="loading" class="picker-note">正在选题…</text>
    <text v-else-if="error" class="ui-error">{{ error }}</text>
    <text v-else-if="selection" class="picker-note">{{ selection.actualCount ? `已选 ${selection.actualCount} 题${selection.actualCount < config.count ? `，当前范围不足 ${config.count} 题` : ''}` : '当前练法暂无匹配题目，可切换练法。' }}</text>
    <button v-if="!fixedIds.length" class="ui-link" :disabled="disabled || loading" @tap="refresh">{{ error ? '重试选题' : '重新选题' }}</button>
    <button class="ui-link" :disabled="disabled" @tap="changeDirection">返回选择考试方向</button>
  </view>
</template>
<script setup>
import { computed, onMounted, ref, watch } from 'vue'
import { onHide, onUnload, onShow } from '@dcloudio/uni-app'
import MotionSegmented from './MotionSegmented.vue'
import { selectTargetedPractice } from '../api/targetedPerformance'
import { copy, practiceModes, performanceScopeSummary } from '../utils/targetedPerformance.mjs'
import { createCancellation } from '../utils/cancellation.mjs'
import { TOKEN_STORAGE_KEY, PROVINCES } from '../utils/constants'
import { useUserStore } from '../stores/user'
const props = defineProps({ context: { type: Object, required: true }, fixedIds: { type: Array, default: () => [] }, disabled: Boolean })
const emit = defineEmits(['selected', 'loading'])
const userStore = useUserStore()
const config = ref(copy(props.context)), loading = ref(false), error = ref(''), selection = ref(null)
const scopeLabel = computed(() => performanceScopeSummary(config.value.target, PROVINCES))
const modes = computed(() => config.value.mode === 'review' || selection.value?.actualCount === 0 ? practiceModes : practiceModes.slice(0, 2))
let generation = 0, task, mounted = false
function cancel() { generation++; task?.cancel(); loading.value = false; emit('loading', false) }
watch(() => userStore.token, () => {
  cancel(); selection.value = null; error.value = ''
  emit('selected', { questionIds: [], targetedContext: copy(config.value) })
}, { flush: 'sync' })
onHide(cancel); onUnload(cancel)
onMounted(() => { mounted = true; refresh() })
onShow(() => { if (mounted && !selection.value) refresh() })
async function refresh() {
  cancel()
  const id = generation, token = uni.getStorageSync(TOKEN_STORAGE_KEY)
  selection.value = null; error.value = ''; loading.value = true
  emit('selected', { questionIds: [], targetedContext: copy(config.value) }); emit('loading', true)
  task = createCancellation()
  try {
    const { version, rulesVersion, ...request } = config.value
    const response = props.fixedIds.length
      ? { questionIds: [...props.fixedIds], actualCount: props.fixedIds.length, targetedContext: copy(config.value) }
      : await selectTargetedPractice(request, { signal: task.signal })
    if (id !== generation || token !== uni.getStorageSync(TOKEN_STORAGE_KEY)) return
    selection.value = response
    emit('selected', response)
  } catch (e) { if (id === generation && token === uni.getStorageSync(TOKEN_STORAGE_KEY)) error.value = e.message || '选题失败，请重试' }
  finally { if (id === generation) { loading.value = false; emit('loading', false) } }
}
function changeMode(value) { if (props.disabled) return; config.value.mode = value; refresh() }
function changeCount(value) { if (props.disabled) return; config.value.count = value; refresh() }
function changeDirection() { uni.switchTab({ url: '/pages/targeted/index' }) }
</script>
<style scoped>
.count-options { display:flex; align-items:center; gap:12rpx; margin:24rpx 0; font-size:26rpx; }
.count-option { margin:0; padding:0 18rpx; font-size:26rpx; background:var(--ui-soft); color:var(--ui-text); }
.count-option.selected { background:var(--ui-primary, #326be5); color:white; }
.picker-note { display:block; font-size:25rpx; line-height:1.7; margin-top:16rpx; color:var(--ui-muted); }
</style>
