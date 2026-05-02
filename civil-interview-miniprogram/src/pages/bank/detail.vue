<template>
  <view class="page">
    <view v-if="question" class="detail">
      <QuestionCard :question="question" />

      <view class="card">
        <view class="section-head">
          <text class="section-title">采分点</text>
          <text class="muted">{{ scoringPoints.length }} 项</text>
        </view>
        <view v-if="scoringPoints.length">
          <view v-for="(point, index) in scoringPoints" :key="index" class="point">
            <text class="point__index">{{ index + 1 }}</text>
            <text class="point__content">{{ point.content || point.name }}</text>
            <text class="point__score">{{ point.score || 0 }} 分</text>
          </view>
        </view>
        <EmptyState v-else title="暂无采分点" />
      </view>

      <button class="primary-button" @tap="startPractice">练这道题</button>
    </view>
    <view v-else class="card">
      <EmptyState title="题目加载中" />
    </view>
  </view>
</template>

<script setup>
import { computed, ref } from 'vue'
import { onLoad } from '@dcloudio/uni-app'
import EmptyState from '../../components/EmptyState.vue'
import QuestionCard from '../../components/QuestionCard.vue'
import { useExamStore } from '../../stores/exam'
import { useQuestionBankStore } from '../../stores/questionBank'
import { hideLoading, requireLogin, showLoading, toast } from '../../utils/navigation'

const bankStore = useQuestionBankStore()
const examStore = useExamStore()
const questionId = ref('')
const question = computed(() => bankStore.currentQuestion)
const scoringPoints = computed(() => Array.isArray(question.value?.scoringPoints) ? question.value.scoringPoints : [])

onLoad(async (query) => {
  if (!requireLogin()) return
  questionId.value = query?.id || ''
  if (!questionId.value) {
    toast('题目不存在')
    return
  }
  showLoading('加载题目')
  try {
    await bankStore.fetchQuestion(questionId.value)
  } finally {
    hideLoading()
  }
})

async function startPractice() {
  if (!question.value) return
  showLoading('创建考场')
  try {
    await examStore.startFromQuestions([question.value], 'bank')
    uni.navigateTo({ url: '/pages/exam/room' })
  } catch (error) {
    toast(error?.message || '无法开始练习')
  } finally {
    hideLoading()
  }
}
</script>

<style scoped>
.point {
  display: grid;
  grid-template-columns: 48rpx minmax(0, 1fr) 88rpx;
  gap: 12rpx;
  padding: 18rpx 0;
  border-bottom: 1rpx solid #eef2f6;
}

.point:last-child {
  border-bottom: 0;
}

.point__index {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 44rpx;
  height: 44rpx;
  border-radius: 999rpx;
  background: #e8f4fd;
  color: #1b5faa;
  font-size: 24rpx;
  font-weight: 700;
}

.point__content {
  color: #2a3648;
  font-size: 27rpx;
  line-height: 1.6;
}

.point__score {
  color: #d48806;
  font-size: 24rpx;
  text-align: right;
}
</style>
