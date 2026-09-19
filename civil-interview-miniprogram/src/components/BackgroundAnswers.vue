<template>
  <view v-if="pending.length || examStore.finishError" class="background-answers">
    <view class="background-answers__head"><LearnerIcon name="cloud-upload" :size="20" /><text>{{ pending.length }} 题待处理</text><text>可继续站内操作</text></view>
    <text class="background-answers__hint">完成前请保持小程序打开，勿清理或退出账号。</text>
    <view v-for="answer in pending" :key="`${answer.examId}:${answer.questionIndex}`" class="background-answers__row">
      <text>{{ answer.examId === examStore.examId ? '本场' : '其他场次' }}第 {{ answer.questionIndex + 1 }} 题 · {{ labels[answer.processingStatus] || '等待处理' }}</text>
      <button v-if="answer.processingStatus === 'failed'" size="mini" @tap="retry(answer)">重试</button>
      <button v-if="answer.examId !== examStore.examId" size="mini" @tap="openResult(answer)">查看原文</button>
      <view class="background-answers__steps">
        <view v-for="(step, index) in submissionProgress(answer)" :key="step.label" class="background-answers__step" :class="`stage--${step.state}`">
          <LearnerIcon :name="step.state === 'done' ? 'check-circle' : step.state === 'failed' ? 'reload' : stageIcons[index]" :size="16" />
          <text>{{ step.label }}{{ step.state === 'failed' ? '重试' : step.state === 'done' ? '完成' : '' }}</text>
        </view>
      </view>
      <text v-if="answer.processingError" class="background-answers__error">{{ answer.processingError }}</text>
    </view>
    <view v-if="examStore.finishError" class="background-answers__row"><text>{{ examStore.finishError }}</text><button size="mini" @tap="examStore.finish()">同步记录</button></view>
  </view>
</template>
<script setup>
import { computed } from 'vue'
import { useExamStore } from '../stores/exam'
import LearnerIcon from './LearnerIcon.vue'
import { submissionProgress } from '../utils/submissionProgress'
const examStore = useExamStore()
const stageIcons = ['cloud-upload', 'file-text', 'solution']
const labels = { queued: '本机暂存', uploading: '上传中', transcribing: '转写中', scoring: '点评中', failed: '处理未完成' }
const pending = computed(() => examStore.pendingAnswers)
function retry(answer) { void examStore.retryAnswer(answer) }
function openResult(answer) { uni.navigateTo({ url: `/pages/result/index?examId=${encodeURIComponent(answer.examId)}&questionId=${encodeURIComponent(answer.questionId)}` }) }
</script>
<style scoped>
.background-answers { margin: 16rpx 0; padding: 24rpx; border-radius: 24rpx; background: #edf5ff; color: #233d64; font-size: 26rpx; }
.background-answers__head, .background-answers__row { display: flex; justify-content: space-between; align-items: center; gap: 16rpx; flex-wrap: wrap; }
.background-answers__head { font-weight: 600; }
.background-answers__hint { display: block; margin-top: 12rpx; color: #53647c; font-size: 23rpx; }
.background-answers__row { margin-top: 16rpx; }
.background-answers__row button { margin: 0; color: #245bc7; background: #fff; }
.background-answers__steps { display: flex; flex-basis: 100%; gap: 12rpx; margin: 8rpx 0; }
.background-answers__step { display: flex; flex: 1; align-items: center; gap: 8rpx; padding-top: 14rpx; border-top: 6rpx solid #c3d0e2; color: #596a80; font-size: 23rpx; }
.background-answers__step.stage--done { color: #147d74; border-color: #147d74; }
.background-answers__step.stage--active { color: #285bc7; border-color: #326be5; font-weight: 600; }
.background-answers__step.stage--failed { color: #a94b2b; border-color: #a94b2b; }
.background-answers__error { flex-basis: 100%; color: #9a5220; font-size: 24rpx; }
</style>
