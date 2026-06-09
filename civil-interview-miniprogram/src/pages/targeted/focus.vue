<!--
这个小程序页面展示重点分析；它只消费真实题库统计或管理员发布内容，没有数据时不要展示通用模板。

@param: 无；页面运行时从 props、路由参数、Pinia 状态和用户点击中拿数据。
@return: 渲染当前业务界面，并把按钮、表单或跳转事件交给既有流程处理。
@raises: 不主动抛业务异常；接口失败、未登录和权限不足由请求层或页面提示承接。
-->
<template>
  <view class="page">
    <view class="focus-header">
      <text class="back-link" @tap="goBack">← 返回</text>
      <text class="page-title">重点分析</text>
    </view>
    <text class="page-desc">根据真实考试方向整理高频考点、能力重点和备考策略。</text>

    <view v-if="selectionTags.length" class="selection-card">
      <text v-for="tag in selectionTags" :key="tag" class="selection-tag">{{ tag }}</text>
    </view>

    <view v-if="targetedStore.focusLoading" class="card loading-card motion-shimmer">
      <text class="loading-card__title">AI正在分析面试重点...</text>
      <text class="loading-card__desc">请稍候，系统正在根据省份和岗位整理核心考点。</text>
    </view>

    <view v-else-if="isEmptyFocus" class="card">
      <EmptyState title="暂无足够题库数据" :desc="targetedStore.focusData?.emptyMessage || '请选择已有真实题库的考试方向后再试。'" />
    </view>

    <view v-else-if="targetedStore.focusData" class="focus">
      <view v-if="coreFocus.length" class="card">
        <view class="section-head">
          <text class="section-title">核心能力权重</text>
        </view>
        <view v-for="item in coreFocus" :key="item.name" class="focus-row">
          <view class="focus-row__head">
            <text>{{ item.name }}</text>
            <text>{{ item.weight || 20 }}%</text>
          </view>
          <view class="focus-row__track">
            <view class="focus-row__bar" :style="{ width: `${item.weight || 20}%` }" />
          </view>
          <text class="focus-row__desc">{{ item.desc }}</text>
        </view>
      </view>

      <view v-if="highFreqTypes.length" class="card">
        <view class="section-head">
          <text class="section-title">高频题型</text>
        </view>
        <view v-for="item in highFreqTypes" :key="item.type" class="list-item">
          <view class="list-item__head">
            <text class="list-item__title">{{ item.type }}</text>
            <text class="freq-tag" :style="{ background: freqColorBg(item.frequency), color: freqColor(item.frequency) }">{{ item.frequency || '中' }}频</text>
          </view>
          <text class="list-item__desc">{{ item.example || '结合岗位实际进行展开。' }}</text>
        </view>
      </view>

      <view v-if="hotTopics.length" class="card">
        <view class="section-head">
          <text class="section-title">热门话题</text>
        </view>
        <view class="topic-cloud">
          <text v-for="topic in hotTopics" :key="topic" class="topic-tag">{{ topic }}</text>
        </view>
      </view>

      <view v-if="strategy.length" class="card">
        <view class="section-head">
          <text class="section-title">备考策略</text>
        </view>
        <view v-for="(item, idx) in strategy" :key="idx" class="strategy-item">
          <text class="strategy-item__num">{{ idx + 1 }}</text>
          <text class="strategy-item__text">{{ item }}</text>
        </view>
      </view>
    </view>
    <view v-else-if="!targetedStore.focusLoading" class="card">
      <EmptyState title="暂无分析结果" desc="请回到定向备面页选择方向后再试。" />
    </view>

    <view v-if="targetedStore.generatedQuestions.length" class="card generated-practice">
      <view class="generated-practice__header">
        <view>
          <text class="generated-practice__title">已生成题目</text>
          <text class="generated-practice__desc">先查看题目，再点击开始练习进入设备检测和练习模式选择。</text>
        </view>
        <button class="primary-button" @tap="startGeneratedPractice">开始练习</button>
      </view>
      <view
        v-for="(question, index) in targetedStore.generatedQuestions"
        :key="question.id || index"
        class="generated-practice__item"
      >
        <text class="generated-practice__idx">{{ index + 1 }}</text>
        <text class="generated-practice__stem">{{ question.stem }}</text>
      </view>
    </view>

    <view class="focus-actions">
      <button class="primary-button" :disabled="readonlyMode" :loading="targetedStore.focusLoading" @tap="loadFocus">刷新分析</button>
      <button v-if="!isEmptyFocus" class="secondary-button" :disabled="readonlyMode" :loading="generateLoading" @tap="generateQuestions">生成针对性题目</button>
    </view>
  </view>
</template>

<script setup>
import { computed, ref } from 'vue'
import { onLoad } from '@dcloudio/uni-app'
import EmptyState from '../../components/EmptyState.vue'
import { useBillingStore } from '../../stores/billing'
import { useSubscriptionStore } from '../../stores/subscription'
import { useTargetedStore } from '../../stores/targeted'
import { useUserStore } from '../../stores/user'
import { hasPremiumAccess } from '../../utils/access'
import { hideLoading, requireLogin, showLoading, toast } from '../../utils/navigation'

const billingStore = useBillingStore()
const subscriptionStore = useSubscriptionStore()
const targetedStore = useTargetedStore()
const userStore = useUserStore()
const generateLoading = ref(false)
const hasFullAccess = computed(() => hasPremiumAccess(userStore, billingStore, subscriptionStore))
const readonlyMode = computed(() => !hasFullAccess.value)
const coreFocus = computed(() => Array.isArray(targetedStore.focusData?.coreFocus) ? targetedStore.focusData.coreFocus : [])
const highFreqTypes = computed(() => Array.isArray(targetedStore.focusData?.highFreqTypes) ? targetedStore.focusData.highFreqTypes : [])
const hotTopics = computed(() => Array.isArray(targetedStore.focusData?.hotTopics) ? targetedStore.focusData.hotTopics : [])
const strategy = computed(() => Array.isArray(targetedStore.focusData?.strategy) ? targetedStore.focusData.strategy : [])
const selectionTags = computed(() => {
  const payload = targetedStore.selectedTarget || targetedStore.selectionPayload || {}
  return [
    payload.examCategory,
    payload.examSubcategory,
    payload.system || payload.positionType || payload.portalTag,
    payload.targetName
  ].filter((item, index, array) => item && array.indexOf(item) === index)
})
const isEmptyFocus = computed(() => (
  targetedStore.focusData?.isFallback === true || Number(targetedStore.focusData?.questionCount || 0) <= 0
))

onLoad(async (options = {}) => {
  if (!requireLogin()) return
  // syncSelection() already called setTarget() before navigation — prefer store data
  if (!targetedStore.hasSelection) {
    applyRouteSelection(options)
  }
  await refreshAccessState().catch(() => null)
  if (!targetedStore.hasSelection) {
    toast('请先选择考试方向')
    uni.navigateBack()
    return
  }
  if (!targetedStore.focusData) await loadFocus()
})

function applyRouteSelection(options = {}) {
  const payload = {}
  const keys = [
    'province', 'position', 'examCategory', 'examSubcategory',
    'system', 'positionType', 'portalTag', 'displayPortal',
    'targetCode', 'targetName', 'year'
  ]
  keys.forEach((key) => {
    const raw = String(options[key] || '').trim()
    if (!raw) return
    let value = raw
    try {
      if (raw.includes('%')) value = decodeURIComponent(raw)
    } catch { /* keep raw */ }
    if (value) payload[key] = value
  })
  if (payload.targetCode || payload.examCategory || payload.targetName) {
    targetedStore.setTarget(payload)
    return
  }
  if (payload.province) targetedStore.setSelection(payload.province, payload.position || '')
}

async function refreshAccessState() {
  if (!userStore.isAuthenticated) return
  await Promise.allSettled([
    userStore.loadUserInfo(),
    subscriptionStore.refresh({ skipErrorHandler: true })
  ])
}

async function loadFocus() {
  if (readonlyMode.value) return
  if (!targetedStore.hasSelection) {
    toast('请先选择考试方向')
    uni.navigateBack()
    return
  }
  showLoading('分析中')
  try {
    await targetedStore.fetchFocusAnalysis()
  } catch (error) {
    toast(error?.message || '分析失败')
  } finally {
    hideLoading()
  }
}

function freqColor(freq) {
  if (freq === '高') return '#cf1322'
  if (freq === '中') return '#d48806'
  return '#8c8c8c'
}

function freqColorBg(freq) {
  if (freq === '高') return 'rgba(207, 19, 34, 0.08)'
  if (freq === '中') return 'rgba(212, 136, 6, 0.08)'
  return 'rgba(140, 140, 140, 0.08)'
}

function goBack() {
  uni.navigateBack()
}

function startGeneratedPractice() {
  if (!targetedStore.generatedQuestions.length) {
    toast('请先生成针对性题目')
    return
  }
  uni.navigateTo({ url: '/pages/exam/prepare?source=targeted' })
}

async function generateQuestions() {
  if (readonlyMode.value || generateLoading.value) return
  generateLoading.value = true
  showLoading('生成题目')
  try {
    const questions = await targetedStore.fetchGeneratedQuestions(5)
    if (questions && questions.length) {
      toast(`已生成 ${questions.length} 道题目`, 'success')
    }
  } catch (error) {
    toast(error?.message || '生成失败')
  } finally {
    generateLoading.value = false
    hideLoading()
  }
}
</script>

<style scoped>
.focus-header {
  display: flex;
  align-items: center;
  gap: 16rpx;
  margin-bottom: 8rpx;
}

.back-link {
  color: #2F7FD6;
  font-size: 27rpx;
  flex-shrink: 0;
}

.focus-row {
  margin-bottom: 24rpx;
}

.selection-card {
  display: flex;
  flex-wrap: wrap;
  gap: 12rpx;
  margin: 8rpx 0 24rpx;
}

.selection-tag {
  padding: 8rpx 18rpx;
  border-radius: 999rpx;
  background: #EAF5FF;
  color: #2F7FD6;
  font-size: 23rpx;
  font-weight: 600;
}

.focus-row:last-child {
  margin-bottom: 0;
}

.focus-row__head {
  display: flex;
  justify-content: space-between;
  color: #2a3648;
  font-size: 27rpx;
  font-weight: 700;
}

.focus-row__track {
  overflow: hidden;
  height: 12rpx;
  margin-top: 12rpx;
  border-radius: 999rpx;
  background: #edf2f7;
}

.focus-row__bar {
  height: 100%;
  border-radius: 999rpx;
  background: #2F7FD6;
  transition: width 300ms ease-out;
}

.focus-row__desc {
  display: block;
  margin-top: 10rpx;
  color: #64748B;
  font-size: 24rpx;
  line-height: 1.6;
}

.list-item {
  padding: 20rpx 0;
  border-bottom: 1rpx solid #eef2f6;
}

.list-item:last-child {
  border-bottom: 0;
}

.list-item__head {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 6rpx;
}

.list-item__title,
.list-item__desc,
.strategy-item__text {
  display: block;
}

.loading-card__title {
  display: block;
  color: #172033;
  font-size: 28rpx;
  font-weight: 700;
}

.loading-card__desc {
  display: block;
  margin-top: 10rpx;
  color: #64748B;
  font-size: 24rpx;
  line-height: 1.6;
}

.list-item__title {
  color: #172033;
  font-size: 28rpx;
  font-weight: 700;
}

.list-item__desc,
.strategy-item {
  margin-top: 8rpx;
  color: #64748B;
  font-size: 24rpx;
  line-height: 1.6;
}

.strategy-item {
  display: flex;
  align-items: flex-start;
  gap: 16rpx;
  padding: 14rpx 0;
  font-size: 27rpx;
  color: #2a3648;
  line-height: 1.5;
}

.strategy-item__num {
  width: 44rpx;
  height: 44rpx;
  border-radius: 50%;
  background: #2F7FD6;
  color: #fff;
  font-size: 24rpx;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
  animation: strategy-num-pop 220ms ease-out both;
}

.topic-cloud {
  display: flex;
  flex-wrap: wrap;
  gap: 14rpx;
}

.topic-tag {
  padding: 10rpx 20rpx;
  border-radius: 999rpx;
  background: #fef7e8;
  color: #8c6d1f;
  font-size: 24rpx;
}

.freq-tag {
  padding: 6rpx 16rpx;
  border-radius: 999rpx;
  font-size: 22rpx;
  font-weight: 600;
  flex-shrink: 0;
}

.generated-practice {
  margin-top: 16rpx;
}

.generated-practice__header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16rpx;
  margin-bottom: 24rpx;
}

.generated-practice__title {
  display: block;
  color: #172033;
  font-size: 28rpx;
  font-weight: 700;
  margin-bottom: 6rpx;
}

.generated-practice__desc {
  display: block;
  color: #64748B;
  font-size: 24rpx;
}

.generated-practice__item {
  display: flex;
  align-items: flex-start;
  gap: 16rpx;
  padding: 22rpx 0;
  border-top: 1rpx solid #eef2f6;
}

.generated-practice__idx {
  width: 44rpx;
  height: 44rpx;
  border-radius: 50%;
  background: #EAF5FF;
  color: #2F7FD6;
  font-size: 24rpx;
  font-weight: 600;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
}

@keyframes strategy-num-pop {
  from {
    opacity: 0;
    transform: scale(0.78);
  }
  to {
    opacity: 1;
    transform: scale(1);
  }
}

.generated-practice__stem {
  color: #2a3648;
  font-size: 27rpx;
  line-height: 1.75;
  flex: 1;
}

.focus-actions {
  display: flex;
  flex-direction: column;
  gap: 16rpx;
  margin-top: 24rpx;
}
</style>
