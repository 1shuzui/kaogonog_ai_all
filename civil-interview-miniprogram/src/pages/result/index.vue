<template>
  <view class="page">
    <template v-if="result">
      <view class="result-hero card">
        <view class="result-hero__copy">
          <text class="result-hero__kicker">模型评测结果</text>
          <text class="result-hero__score">{{ result.totalScore }}/{{ result.maxScore }} 分</text>
          <text class="result-hero__grade" :style="{ color: grade.color }">{{ grade.label }}</text>
        </view>
        <ScoreRing :score="result.totalScore" :max-score="result.maxScore" size="medium" :color="grade.color" />
      </view>

      <view v-if="questionStem" class="card">
        <view class="section-head">
          <text class="section-title">题目</text>
        </view>
        <text class="plain-text">{{ questionStem }}</text>
      </view>

      <view class="card">
        <view class="section-head">
          <text class="section-title">AI 评语</text>
        </view>
        <text class="plain-text">{{ result.aiComment }}</text>
      </view>

      <view class="card">
        <view class="section-head">
          <text class="section-title">维度表现</text>
        </view>
        <DimensionBars :dimensions="result.dimensions" />
      </view>

      <view v-if="transcript" class="card">
        <view class="section-head">
          <text class="section-title">作答文本</text>
        </view>
        <text class="plain-text">{{ transcript }}</text>
      </view>

      <view class="result-actions">
        <button class="primary-button" @tap="again">再练一题</button>
        <button class="secondary-button" @tap="home">返回首页</button>
      </view>
    </template>
    <view v-else class="card">
      <EmptyState title="暂无评分结果" desc="如果刚提交作答，请稍后刷新历史记录。" />
    </view>
  </view>
</template>

<script setup>
import { computed, ref } from 'vue'
import { onLoad } from '@dcloudio/uni-app'
import DimensionBars from '../../components/DimensionBars.vue'
import EmptyState from '../../components/EmptyState.vue'
import ScoreRing from '../../components/ScoreRing.vue'
import { getHistoryDetail } from '../../api/history'
import { getScoringResult } from '../../api/scoring'
import { useExamStore } from '../../stores/exam'
import { useTrainingStore } from '../../stores/training'
import { getGrade } from '../../utils/constants'
import { hideLoading, requireLogin, showLoading, toast } from '../../utils/navigation'
import { normalizeResult } from '../../utils/scoring'

const examStore = useExamStore()
const trainingStore = useTrainingStore()
const result = ref(null)
const transcript = ref('')
const questionStem = ref('')
const progressRecorded = ref(false)

const grade = computed(() => getGrade(result.value?.totalScore || 0, result.value?.maxScore || 100))

onLoad(async (query) => {
  if (!requireLogin()) return
  await loadResult(query || {})
})

async function loadResult(query) {
  const examId = query.examId || examStore.examId
  const questionId = query.questionId || examStore.currentQuestion?.id
  const answer = examStore.answers.find((item) => item.questionId === questionId) || examStore.answers[examStore.answers.length - 1]

  if (answer?.scoringResult) {
    result.value = normalizeResult(answer.scoringResult)
    transcript.value = answer.transcript || ''
    questionStem.value = answer.questionStem || ''
    recordTrainingProgress()
    return
  }

  showLoading('加载结果')
  try {
    if (examId && questionId) {
      result.value = normalizeResult(await getScoringResult(examId, questionId))
      recordTrainingProgress()
      return
    }

    if (examId) {
      const detail = await getHistoryDetail(examId)
      const firstAnswer = Array.isArray(detail?.answers) ? detail.answers[0] : null
      if (firstAnswer?.scoringResult) {
        result.value = normalizeResult(firstAnswer.scoringResult)
        transcript.value = firstAnswer.transcript || ''
        questionStem.value = firstAnswer.questionStem || detail.questionSummary || ''
        recordTrainingProgress()
        return
      }
      result.value = normalizeResult(detail)
      questionStem.value = detail?.questionSummary || ''
      recordTrainingProgress()
    }
  } catch (error) {
    toast(error?.message || '结果加载失败')
  } finally {
    hideLoading()
  }
}

function recordTrainingProgress() {
  const source = String(examStore.source || '')
  if (progressRecorded.value || !source.startsWith('training:') || !result.value) return
  const key = source.replace('training:', '')
  trainingStore.recordResult(key, result.value.totalScore)
  progressRecorded.value = true
}

function again() {
  uni.redirectTo({ url: '/pages/exam/prepare' })
}

function home() {
  uni.switchTab({ url: '/pages/home/index' })
}
</script>

<style scoped>
.result-hero {
  display: flex;
  align-items: center;
  justify-content: space-between;
  background: #ffffff;
}

.result-hero__copy {
  min-width: 0;
}

.result-hero__kicker,
.result-hero__score,
.result-hero__grade,
.plain-text {
  display: block;
}

.result-hero__kicker {
  color: #6f7c8f;
  font-size: 24rpx;
}

.result-hero__score {
  margin-top: 8rpx;
  color: #1a1a2e;
  font-size: 52rpx;
  font-weight: 900;
}

.result-hero__grade {
  margin-top: 4rpx;
  font-size: 28rpx;
  font-weight: 800;
}

.plain-text {
  color: #2a3648;
  font-size: 27rpx;
  line-height: 1.75;
  white-space: pre-wrap;
}

.result-actions {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 16rpx;
}
</style>
