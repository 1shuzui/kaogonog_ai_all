<template>
  <section v-if="pending.length || examStore.finishError" class="background-answers" aria-live="polite" aria-label="后台处理进度">
    <div class="background-answers__head"><CloudUploadOutlined /><strong>{{ hasRunning ? '作答已暂存，后台继续处理' : '作答仍保留，请重试未完成的处理' }}</strong><span>{{ pending.length }} 题待处理</span></div>
    <p>可继续站内操作；处理完成前，请不要刷新或关闭页面。</p>
    <div v-for="answer in pending" :key="`${answer.examId}:${answer.questionIndex}`" class="background-answers__row">
      <span>{{ answer.examId === examStore.examId ? '本场' : '其他场次' }}第 {{ answer.questionIndex + 1 }} 题 · {{ labels[answer.processingStatus] || '等待处理' }}</span>
      <a-button v-if="answer.processingStatus === 'failed'" size="small" @click="retry(answer)"><ReloadOutlined /> 重试</a-button>
      <span v-else class="background-answers__pulse" aria-hidden="true"></span>
      <router-link v-if="answer.examId !== examStore.examId" :to="`/result/${answer.examId}`">查看原文</router-link>
      <ol class="background-answers__steps" aria-label="处理阶段">
        <li v-for="(step, index) in submissionProgress(answer)" :key="step.label" :class="`stage--${step.state}`" :aria-current="step.state === 'active' ? 'step' : undefined">
          <CheckCircleOutlined v-if="step.state === 'done'" />
          <ExclamationCircleOutlined v-else-if="step.state === 'failed'" />
          <component :is="stageIcons[index]" v-else />
          <span>{{ step.label }}{{ step.state === 'failed' ? '重试' : step.state === 'done' ? '完成' : '' }}</span>
        </li>
      </ol>
      <small v-if="answer.processingError">{{ answer.processingError }}</small>
    </div>
    <div v-if="examStore.finishError" class="background-answers__row"><span>{{ examStore.finishError }}</span><a-button size="small" @click="examStore.finish()">同步练习记录</a-button></div>
  </section>
</template>

<script setup>
import { computed, onMounted, onUnmounted } from 'vue'
import { CloudUploadOutlined, ReloadOutlined, FileTextOutlined, SolutionOutlined, CheckCircleOutlined, ExclamationCircleOutlined } from '@ant-design/icons-vue'
import { useExamStore } from '@/stores/exam'
import { submissionProgress } from '@/utils/submissionProgress'
const examStore = useExamStore()
const stageIcons = [CloudUploadOutlined, FileTextOutlined, SolutionOutlined]
const labels = { queued: '本机暂存', uploading: '上传中', transcribing: '转写中', scoring: '点评中', failed: '处理未完成' }
const pending = computed(() => examStore.pendingAnswers)
const hasRunning = computed(() => pending.value.some((answer) => answer.processingStatus !== 'failed'))
function retry(answer) { void examStore.retryAnswer(answer) }
function protectPending(event) {
  if (!pending.value.length) return
  event.preventDefault()
  event.returnValue = ''
}
onMounted(() => window.addEventListener('beforeunload', protectPending))
onUnmounted(() => window.removeEventListener('beforeunload', protectPending))
</script>

<style scoped>
.background-answers { padding: 16px 20px; margin: 12px 0; border-radius: 14px; background: #edf5ff; color: #233d64; border: 1px solid #d7e6f9; text-align: left; font-size: 14px; }
.background-answers__head { display: flex; align-items: center; gap: 10px; flex-wrap: wrap; }
.background-answers__head > span:last-child { margin-left: auto; font-variant-numeric: tabular-nums; }
.background-answers p { font-size: 12px; margin: 8px 0; color: #53647c; }
.background-answers__row { display: flex; align-items: center; gap: 8px; flex-wrap: wrap; padding-top: 8px; }
.background-answers__row small { flex-basis: 100%; color: #9a5220; }
.background-answers__steps { display: flex; flex-basis: 100%; gap: 8px; padding: 0; margin: 4px 0 8px; list-style: none; }
.background-answers__steps li { display: flex; align-items: center; gap: 6px; flex: 1; padding-top: 8px; border-top: 3px solid #c3d0e2; color: #596a80; font-size: 12px; }
.background-answers__steps .stage--done { color: #147d74; border-color: #147d74; }
.background-answers__steps .stage--active { color: #285bc7; border-color: #326be5; font-weight: 600; }
.background-answers__steps .stage--failed { color: #a94b2b; border-color: #a94b2b; }
.background-answers__pulse { width: 6px; height: 6px; border-radius: 50%; background: #3978ed; animation: job-pulse 1.6s ease-in-out infinite; }
@keyframes job-pulse { 50% { opacity: .3; } }
@media (prefers-reduced-motion: reduce) { .background-answers__pulse { animation: none; } }
</style>
