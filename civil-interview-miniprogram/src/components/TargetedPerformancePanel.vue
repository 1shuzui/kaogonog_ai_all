<template>
  <view v-if="store.status !== 'idle' || store.report" id="performance-report" class="performance card">
    <text class="section-title">当前方向弱点与优势</text>
    <text class="page-desc">{{ scopeLabel }}</text>
    <MotionSegmented :model-value="store.period" :options="periodOptions" @change="changePeriod" />
    <view v-if="store.status === 'loading'" class="performance-state" aria-live="polite">
      <text>{{ store.slow ? '记录较多，仍在读取，请稍候。' : '正在读取已保存成绩…' }}</text>
      <button class="ui-link" @tap="store.cancel()">停止等待</button>
    </view>
    <view v-if="store.error" class="performance-state" aria-live="polite">
      <text class="ui-error">{{ store.error }}</text><button class="ui-link" @tap="store.fetch()">重新分析</button>
    </view>
    <template v-if="store.report">
      <text class="performance-date">{{ store.status !== 'success' ? '上次结果 · ' : '' }}更新于 {{ displayDate(store.report.updatedAt) }}</text>
      <text class="performance-conclusion">{{ store.report.conclusion }}</text>
      <text class="performance-basis">{{ store.report.summary.sampleCount }} 道不同题目 · {{ store.report.summary.judgedTypeCount }} 类题型可判断</text>
      <text v-if="store.report.summary.pendingCount" class="performance-basis">{{ store.report.summary.pendingCount }} 条作答待点评，完成后可刷新分析。</text>
      <text v-if="!store.report.summary.sampleCount" class="performance-basis">当前范围尚无可计入的成绩，可先练习下方题型。</text>
      <view v-for="row in store.report.questionTypes" :key="row.questionType" class="performance-type">
        <view class="performance-heading"><text>{{ row.questionType }}</text><text :class="`performance-label--${row.status}`">{{ row.label }}</text></view>
        <view class="performance-score"><text>{{ row.percentText }}</text><text class="muted">内容得分率 · {{ row.sampleCount }} 道题</text></view>
        <view class="performance-track" aria-hidden="true"><view :class="`performance-fill--${row.status}`" :style="{ width: `${row.averagePercent ?? 0}%` }" /></view>
        <text v-if="!row.availableCount" class="performance-basis">当前方向暂无可练题目</text>
        <view class="performance-actions">
          <button class="secondary-button" @tap="openDetails(row)">查看答题记录</button>
          <button class="primary-button" :disabled="!row.availableCount" @tap="practice(row)">{{ practiceLabel(row) }}</button>
        </view>
      </view>
      <button class="ui-link" :aria-expanded="showRules" @tap="showRules = !showRules">{{ showRules ? '收起统计说明' : '统计标准与未纳入记录' }}</button>
      <view v-if="showRules" class="performance-rules">
        <text>按成绩记录时间统计，同题取最近有效成绩，每题等权；内容分不含仪态分。</text>
        <text>每题型至少 {{ store.report.rules.minSamples }} 道不同题目才判断表现：低于 {{ store.report.rules.lowThreshold }}% 优先提升，达到 {{ store.report.rules.highThreshold }}% 较擅长，其余需巩固。</text>
        <text>分析标准独立于错题本个人低分线。题源年份与成绩记录时间分别筛选；重评会更新成绩记录时间。</text>
        <text v-for="(count, reason) in store.report.summary.excluded" :key="reason">{{ reasonLabel(reason) }}：{{ count }} 条</text>
        <text v-if="store.report.summary.unattributedCount">另有 {{ store.report.summary.unattributedCount }} 条记录因题目已移除，无法确定方向，未计入本报告。</text>
        <text>分数反映已练样本；题目、统计窗口或规则变化也可能改变均分。</text>
      </view>
    </template>
  </view>
</template>
<script setup>
import { computed, ref } from 'vue'
import MotionSegmented from './MotionSegmented.vue'
import { useTargetedPerformanceStore } from '../stores/targetedPerformance'
import { periodOptions, performanceDetailUrl, practiceContext, targetedPracticeUrl, performanceScopeSummary } from '../utils/targetedPerformance.mjs'
import { PROVINCES } from '../utils/constants'
const store = useTargetedPerformanceStore()
const showRules = ref(false)
const scopeLabel = computed(() => performanceScopeSummary(store.target || {}, PROVINCES))
const displayDate = value => new Date(value).toLocaleString('zh-CN', { timeZone: 'Asia/Shanghai', hour12: false })
const reasonLabel = reason => ({ pending: '待点评', technical_failure: '技术失败', unreliable_transcript: '无可靠作答', skipped: '已跳过', invalid_score: '分值口径不完整', unclassified: '待分类记录' }[reason] || '未纳入')
const practiceLabel = row => ({ insufficient: '补充练习', unpracticed: '开始练习', strong: '继续巩固' }[row.status] || '针对练习')
function changePeriod(period) { store.setScope(store.target, period); store.fetch() }
function openDetails(row) { uni.navigateTo({ url: performanceDetailUrl(store.target, store.period, row.questionType) }) }
function practice(row) { uni.navigateTo({ url: targetedPracticeUrl(practiceContext(store.target, row.questionType, store.period)) }) }
</script>
<style scoped>
.performance { margin-top:24rpx; }
.performance-date,.performance-basis { display:block; color:var(--ui-muted); font-size:24rpx; line-height:1.7; margin-top:12rpx; }
.performance-conclusion { display:block; color:var(--ui-text); font-size:30rpx; font-weight:600; margin-top:24rpx; }
.performance-type { padding:28rpx 0; border-bottom:1px solid var(--ui-border); }
.performance-heading,.performance-score { display:flex; justify-content:space-between; gap:16rpx; align-items:center; font-size:28rpx; }
.performance-score { margin:18rpx 0; font-size:34rpx; }
.performance-score .muted { font-size:24rpx; }
.performance-label--weak { color:var(--ui-danger, #a33d35); }
.performance-label--strong { color:var(--ui-success, #24746a); }
.performance-label--insufficient,.performance-label--unpracticed { color:var(--ui-muted); }
.performance-track { height:10rpx; background:var(--ui-soft); border-radius:8rpx; overflow:hidden; }
.performance-track>view { height:100%; background:var(--ui-primary, #326be5); }
.performance-track>.performance-fill--weak { background:var(--ui-danger, #a33d35); }
.performance-track>.performance-fill--strong { background:var(--ui-success, #24746a); }
.performance-actions { display:grid; grid-template-columns:1fr 1fr; gap:16rpx; margin-top:24rpx; }
.performance-state { padding:24rpx 0; color:var(--ui-muted); line-height:1.7; }
.performance-rules>text { display:block; margin-top:12rpx; font-size:24rpx; line-height:1.8; color:var(--ui-muted); }
</style>
