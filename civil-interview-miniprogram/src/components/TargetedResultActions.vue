<template>
  <view v-if="context" class="card targeted-result-actions">
    <text class="section-title">{{ context.questionType }} · 本轮针对练习</text>
    <text class="page-desc">{{ pendingCount ? `${pendingCount} 道题仍待点评；分析只纳入已保存的有效成绩。` : context.mode === 'new' ? '新题成绩保存后会增加不同题目的样本。' : '复练成绩按最近有效记录更新，同一道题仍只计一份样本。' }}</text>
    <button class="primary-button" @tap="showPerformance">查看更新后的题型表现</button>
    <button class="secondary-button" @tap="continuePractice">继续练这一类</button>
  </view>
</template>
<script setup>
import { computed } from 'vue'
import { useTargetedPerformanceStore } from '../stores/targetedPerformance'
import { useTargetedStore } from '../stores/targeted'
import { buildTargetFocusUrl } from '../utils/targetedOptions'
import { practiceContext, targetedPracticeUrl } from '../utils/targetedPerformance.mjs'
const props = defineProps({ examId: String, pendingCount: { type: Number, default: 0 } })
const store = useTargetedPerformanceStore(), targetedStore = useTargetedStore()
const context = computed(() => store.contextFor(props.examId))
function showPerformance() {
  const value = context.value
  if (!value) return
  const destination = value.returnView || { target: value.target, period: value.period, scrollTop: 0 }
  store.setScope(destination.target, destination.period)
  store.scrollTop = destination.scrollTop
  store.restorePosition = true
  targetedStore.setTarget(destination.target)
  const pages = getCurrentPages()
  let index = -1
  for (let i = pages.length - 2; i >= 0; i--) {
    if (pages[i].route === destination.route) { index = i; break }
  }
  const fallback = () => uni.navigateTo({ url: `${buildTargetFocusUrl(destination.target)}&period=${destination.period}` })
  if (index >= 0 && index < pages.length - 1) uni.navigateBack({ delta: pages.length - 1 - index, fail: fallback })
  else fallback()
}
function continuePractice() {
  const value = context.value
  if (value) uni.navigateTo({ url: targetedPracticeUrl(practiceContext(value.target, value.questionType, value.period)) })
}
</script>
<style scoped>
.targeted-result-actions { margin:24rpx 0; }
.targeted-result-actions button+button { margin-top:16rpx; }
</style>
