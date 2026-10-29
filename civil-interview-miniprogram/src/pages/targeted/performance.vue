<template>
  <view class="motion-page page" :class="motionClass" :style="motionStyle">
    <text class="page-title">{{ questionType || '题型' }}答题记录</text>
    <text class="page-desc">{{ scopeLabel }} · {{ period === 'all' ? '全部记录' : '近30天' }}</text>
    <view v-if="row" class="card">
      <view class="section-head"><text class="section-title">{{ row.percentText }} · {{ row.label }}</text><text class="muted">{{ row.sampleCount }} 道不同题目</text></view>
      <text class="page-desc">按内容得分率比较，同题只取最近有效成绩。个人低分线不影响本页。</text>
      <button class="primary-button" :disabled="!row.availableCount" @tap="practice()">{{ row.status === 'insufficient' ? '补充练习' : '针对练习' }}</button>
      <view v-for="ability in row.abilities || []" :key="ability.name" class="ability">
        <text>{{ ability.name }} · {{ ability.percentText }}</text><text>{{ ability.sampleCount }} 题 · {{ ability.label }}</text>
      </view>
    </view>
    <MotionSegmented :model-value="recordFilter" :options="filterOptions" @change="changeFilter" />
    <text v-if="changed" class="notice">成绩或统计范围中的数据已更新，以下为最新记录。</text>
    <view v-if="error" class="card"><text class="ui-error">{{ error }}</text><button class="ui-link" @tap="load(false)">重新加载</button></view>
    <view v-for="answer in records" :key="answer.questionId" class="card answer-record">
      <text class="answer-stem">{{ answer.stem }}</text>
      <text class="page-desc">成绩记录时间：{{ displayDate(answer.recordedAt) }}</text>
      <text class="answer-score">内容得分率 {{ answer.percentText }} · 原成绩 {{ answer.score }}/{{ answer.maxScore }}</text>
      <view class="answer-actions"><button class="secondary-button" @tap="review(answer)">查看点评</button><button class="secondary-button" :disabled="!answer.canPractice" @tap="practice(answer)">重新练习</button></view>
    </view>
    <text v-if="loading" class="notice">正在读取答题记录…</text>
    <text v-else-if="!records.length && !error" class="notice">{{ recordFilter === 'low_score' ? '本范围没有低于分析标准的题目。' : '当前题型尚无可计入的成绩，可以先练新题。' }}</text>
    <button v-if="records.length < total" class="secondary-button" :disabled="loading" @tap="load(true)">加载更多</button>
    <button class="ui-link" @tap="back">返回分析</button>
  </view>
</template>
<script setup>
import { computed, ref, watch } from 'vue'
import { onLoad, onShow, onHide, onUnload } from '@dcloudio/uni-app'
import MotionSegmented from '../../components/MotionSegmented.vue'
import { usePageMotion } from '../../motion/useMotion'
import { getPerformanceAnswers } from '../../api/targetedPerformance'
import { createCancellation } from '../../utils/cancellation.mjs'
import { PERFORMANCE_TYPES, practiceContext, targetedPracticeUrl, performanceScopeSummary } from '../../utils/targetedPerformance.mjs'
import { useTargetedPerformanceStore } from '../../stores/targetedPerformance'
import { TOKEN_STORAGE_KEY, PROVINCES } from '../../utils/constants'
import { useUserStore } from '../../stores/user'
import { requireLogin } from '../../utils/navigation'
const { motionClass, motionStyle } = usePageMotion()
const store = useTargetedPerformanceStore()
const userStore = useUserStore()
const target = ref(null), period = ref('recent30'), questionType = ref(''), recordFilter = ref('all')
const records = ref([]), total = ref(0), report = ref(null), error = ref(''), loading = ref(false), changed = ref(false)
const filterOptions = [{ value: 'all', label: '全部计入记录' }, { value: 'low_score', label: '低于分析标准' }]
const scopeLabel = computed(() => performanceScopeSummary(target.value || {}, PROVINCES))
const row = computed(() => report.value?.questionTypes.find(item => item.questionType === questionType.value))
const displayDate = value => new Date(value).toLocaleString('zh-CN', { timeZone: 'Asia/Shanghai', hour12: false })
let generation = 0, task, page = 0, initialized = false
function cancel() { generation++; task?.cancel(); loading.value = false }
watch(() => userStore.token, () => {
  cancel(); records.value = []; total.value = 0; report.value = null
  changed.value = false; error.value = ''; page = 0
}, { flush: 'sync' })
onHide(cancel); onUnload(cancel)
onLoad(options => {
  try {
    let raw = options.target
    try { target.value = JSON.parse(raw) } catch { target.value = JSON.parse(decodeURIComponent(raw)) }
    try { questionType.value = decodeURIComponent(options.questionType || '') } catch { questionType.value = options.questionType || '' }
    period.value = options.period === 'all' ? 'all' : 'recent30'
    if (!target.value || !PERFORMANCE_TYPES.includes(questionType.value)) throw new Error('分析范围不完整，请返回定向备面重新选择')
    initialized = true
  } catch (e) { error.value = e.message || '分析范围读取失败' }
})
onShow(() => { if (initialized && requireLogin()) load(false) })
async function load(append = false) {
  if (!initialized) return
  cancel()
  const id = generation, token = uni.getStorageSync(TOKEN_STORAGE_KEY)
  task = createCancellation()
  loading.value = true; error.value = ''
  try {
    const response = await getPerformanceAnswers({ target: target.value, period: period.value, questionType: questionType.value,
      recordFilter: recordFilter.value, current: append ? page + 1 : 1, pageSize: 20,
      analysisRevision: report.value?.analysisRevision || '' }, { signal: task.signal })
    if (id !== generation || token !== uni.getStorageSync(TOKEN_STORAGE_KEY)) return
    if (append && response.dataChanged) { changed.value = true; await load(false); return }
    changed.value = changed.value || response.dataChanged
    report.value = response.report
    records.value = append ? [...records.value, ...response.list] : response.list
    total.value = response.total; page = response.current
  } catch (e) { if (id === generation && token === uni.getStorageSync(TOKEN_STORAGE_KEY)) error.value = e.message || '读取失败，请重试' }
  finally { if (id === generation) loading.value = false }
}
function changeFilter(value) { recordFilter.value = value; records.value = []; total.value = 0; load(false) }
function review(answer) { uni.navigateTo({ url: `/pages/result/index?examId=${encodeURIComponent(answer.examId)}&questionId=${encodeURIComponent(answer.questionId)}` }) }
function practice(answer) { uni.navigateTo({ url: targetedPracticeUrl(practiceContext(target.value, questionType.value, period.value, answer ? { mode: 'review', count: 1 } : {}), answer ? [answer.questionId] : []) }) }
function back() { store.setScope(target.value, period.value); uni.navigateBack({ fail: () => uni.switchTab({ url: '/pages/targeted/index' }) }) }
</script>
<style scoped>
.answer-record { margin-top:24rpx; }
.answer-stem { display:block; font-size:28rpx; line-height:1.8; }
.answer-score { display:block; font-size:26rpx; color:var(--ui-text); }
.answer-actions { display:grid; grid-template-columns:1fr 1fr; gap:16rpx; margin-top:24rpx; }
.notice { display:block; padding:24rpx 0; color:var(--ui-muted); font-size:26rpx; line-height:1.7; }
.ability { display:flex; justify-content:space-between; gap:16rpx; margin-top:20rpx; font-size:24rpx; color:var(--ui-muted); }
</style>
