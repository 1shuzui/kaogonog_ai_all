<!-- Existing deep-link route; shares the same cancellable task and inline result UI. -->
<template>
  <view class="motion-page page" :class="motionClass" :style="motionStyle">
    <view class="focus-header"><text class="back-link" @tap="goBack">← 返回</text><text class="page-title">重点分析</text></view>
    <text class="page-desc">根据真实考试方向整理高频考点、能力重点和备考策略。</text>
    <text v-if="checkingAccess" class="access-status">正在确认账号权限，可随时返回。</text>
    <FocusAnalysisCard class="focus-detail-analysis" :status="targetedStore.focusStatus" :data="targetedStore.focusData" :error="targetedStore.focusError" :slow="targetedStore.focusSlow" :target-label="targetLabel" @retry="loadFocus" @cancel="targetedStore.cancelFocusAnalysis()" />
    <view v-if="targetedStore.generatedQuestions.length" class="card generated-practice">
      <view class="generated-practice__header"><view><text class="section-title">已生成题目</text><text class="muted">核对题目后进入设备检测和练习模式选择。</text></view><button class="primary-button" @tap="startGeneratedPractice">开始练习</button></view>
      <view v-for="(question, index) in targetedStore.generatedQuestions" :key="question.id || index" class="generated-practice__item"><text class="generated-practice__idx">{{ index + 1 }}</text><text>{{ question.stem }}</text></view>
    </view>
    <view class="focus-actions">
      <button class="primary-button" :disabled="checkingAccess || targetedStore.focusLoading" @tap="loadFocus">刷新分析</button>
      <button v-if="targetedStore.focusData && !isEmptyFocus" class="secondary-button" :disabled="readonlyMode || generateLoading" :loading="generateLoading" @tap="generateQuestions">生成针对性题目</button>
    </view>
  </view>
</template>
<script setup>
import { miniPracticeUrl } from '../../../../shared/practiceSelection.mjs'
import { computed, ref } from 'vue'
import { onLoad, onHide, onUnload } from '@dcloudio/uni-app'
import FocusAnalysisCard from '../../components/FocusAnalysisCard.vue'
import { usePageMotion } from '../../motion/useMotion'
import { useBillingStore } from '../../stores/billing'
import { useSubscriptionStore } from '../../stores/subscription'
import { useTargetedStore } from '../../stores/targeted'
import { useUserStore } from '../../stores/user'
import { hasPremiumAccess } from '../../utils/access'
import { decodeTargetRoute } from '../../utils/targetedOptions'
import { requireLogin, toast } from '../../utils/navigation'
const { motionClass, motionStyle } = usePageMotion()
const billingStore = useBillingStore()
const subscriptionStore = useSubscriptionStore()
const targetedStore = useTargetedStore()
const userStore = useUserStore()
const checkingAccess = ref(false)
const generateLoading = ref(false)
let loadGeneration = 0
const hasFullAccess = computed(() => hasPremiumAccess(userStore, billingStore, subscriptionStore))
const readonlyMode = computed(() => !hasFullAccess.value)
const isEmptyFocus = computed(() => targetedStore.focusData?.isFallback || Number(targetedStore.focusData?.questionCount || 0) <= 0)
const targetLabel = computed(() => {
  const payload = targetedStore.focusParams || targetedStore.selectionPayload || {}
  return [payload.examCategory, payload.examSubcategory, payload.targetName].filter(Boolean).join(' / ')
})
function stopWaiting() { loadGeneration++; checkingAccess.value = false; targetedStore.cancelFocusAnalysis() }
onHide(stopWaiting)
onUnload(stopWaiting)
onLoad(async (options = {}) => {
  if (!requireLogin()) return
  const expected = ++loadGeneration
  if (Object.keys(options).length || !targetedStore.hasSelection) applyRouteSelection(options)
  checkingAccess.value = !hasFullAccess.value
  if (checkingAccess.value) await refreshAccessState().catch(() => null)
  if (expected !== loadGeneration) return
  checkingAccess.value = false
  if (!targetedStore.focusData) loadFocus()
})
function applyRouteSelection(options = {}) {
  const payload = decodeTargetRoute(options)
  if (payload.targetCode || payload.examCategory || payload.targetName) targetedStore.setTarget(payload)
  else if (payload.province) targetedStore.setSelection(payload.province, payload.position || '')
}
async function refreshAccessState() {
  if (!userStore.isAuthenticated) return
  await Promise.allSettled([userStore.loadUserInfo(), subscriptionStore.refresh({ skipErrorHandler: true })])
}
function loadFocus() {
  if (targetedStore.focusLoading || checkingAccess.value) return
  if (readonlyMode.value || !targetedStore.hasSelection) {
    targetedStore.focusStatus = 'error'
    targetedStore.focusError = readonlyMode.value ? '请先开通套餐后使用定向备面' : '请返回定向备面选择考试方向'
    return
  }
  targetedStore.fetchFocusAnalysis().catch(() => null)
}
function goBack() {
  uni.navigateBack({ fail: () => uni.switchTab({ url: '/pages/targeted/index' }) })
}
function startGeneratedPractice() {
  if (!targetedStore.generatedQuestions.length) { toast('请先生成针对性题目'); return }
  uni.navigateTo({ url: miniPracticeUrl({ source: 'targeted', questionIds: targetedStore.generatedQuestions.map(question => question.id), filters: targetedStore.selectionPayload }) })
}
async function generateQuestions() {
  if (readonlyMode.value || generateLoading.value) return
  generateLoading.value = true
  try {
    const questions = await targetedStore.fetchGeneratedQuestions(5)
    if (questions?.length) toast(`已生成 ${questions.length} 道题目`, 'success')
  } catch (error) { toast(error?.message || '生成失败') }
  finally { generateLoading.value = false }
}
</script>
<style scoped>
.focus-header { display:flex; align-items:center; gap:16rpx; margin-bottom:8rpx; }
.back-link { color:#326be5; font-size:27rpx; flex-shrink:0; }
.access-status { display:block; padding:24px 0; color:#64748b; font-size:25rpx; }
.generated-practice__header { display:flex; align-items:center; justify-content:space-between; gap:16rpx; margin-bottom:20rpx; }
.generated-practice__header .muted { display:block; margin-top:8px; }
.generated-practice__item { display:flex; align-items:flex-start; gap:16rpx; padding:22rpx 0; border-top:1rpx solid #eef2f6; color:#35455a; font-size:27rpx; line-height:1.75; }
.generated-practice__idx { flex:none; color:#326be5; font-weight:700; }
.focus-actions { display:flex; flex-direction:column; gap:16rpx; margin-top:24rpx; }
</style>
