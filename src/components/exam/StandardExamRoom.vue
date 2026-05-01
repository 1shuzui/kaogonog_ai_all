<template>
  <div class="exam-room" v-if="examStore.currentQuestion">
    <div v-if="!isOnline" class="exam-room__offline-banner">
      网络已断开，请检查网络连接。录音数据会暂存，恢复网络后可继续提交。
    </div>

    <div class="exam-room__header">
      <span class="exam-room__progress">
        {{ examStore.currentQuestionNumber }} / {{ examStore.totalQuestions }}
      </span>
      <span v-if="examStore.mockMode" class="exam-room__total-timer">
        {{ formattedElapsed }}
      </span>
      <a-popconfirm title="确定退出考试？已答题目不会丢失。" @confirm="exitExam">
        <a-button type="text" size="small" style="color: rgba(255,255,255,0.8)">
          <CloseOutlined /> 退出
        </a-button>
      </a-popconfirm>
    </div>

    <div class="exam-room__main">
      <div class="exam-room__question">
        <QuestionMetaTags :question="examStore.currentQuestion" emphasis :max-keywords="5" />
        <div class="question-stem">
          <QuestionRichContent
            :text="examStore.currentQuestion.stem"
            dark
            scrollable
            :scroll-height="220"
            :collapsed-height="160"
          />
        </div>
      </div>
    </div>

    <div
      class="exam-room__camera"
      :class="{
        'is-pip': examStore.status === 'answering' || examStore.status === 'submitting' || examStore.status === 'completed',
        'is-prep': examStore.status === 'preparing' || examStore.status === 'idle'
      }"
    >
      <VideoPreview
        :stream="stream"
        :recording="examStore.status === 'answering'"
        :duration="recorderDuration"
      />
      <div v-if="examStore.status === 'preparing'" class="camera-hint">
        准备时间，请思考作答思路
      </div>
    </div>

    <div class="exam-room__timer">
      <CountdownTimer
        v-if="examStore.status === 'preparing' || examStore.status === 'answering'"
        :remaining="countdown.remaining.value"
        :total="countdown.total.value"
        :mode="examStore.status === 'preparing' ? 'prep' : 'answer'"
      />
      <div v-else-if="examStore.status === 'submitting'" style="color: rgba(255,255,255,0.7)">
        <a-spin /> <span style="margin-left: 8px">正在评分，请稍候...</span>
      </div>
      <div v-else-if="examStore.status === 'completed'" style="color: #389E0D; font-size: 16px">
        <CheckCircleFilled /> 评分完成
      </div>
    </div>

    <div class="exam-room__waveform" v-show="examStore.status === 'answering'">
      <AudioWaveform
        :stream="stream"
        :active="examStore.status === 'answering'"
        :width="320"
        :height="60"
      />
    </div>

    <div class="exam-room__brief-result" v-if="examStore.status === 'completed' && examStore.scoringResult">
      <div class="brief-score">
        <ScoreRing
          :score="examStore.scoringResult.totalScore"
          :maxScore="examStore.scoringResult.maxScore"
          size="small"
        />
        <span class="brief-score__label">{{ gradeLabel }}</span>
      </div>
    </div>

    <div class="exam-room__controls">
      <RecordingControl
        :status="examStore.status"
        :isLast="examStore.isLastQuestion"
        @start-prep="onStartPrep"
        @start-answer="onStartAnswer"
        @submit="onSubmit"
        @next="onNext"
        @finish="onFinish"
      />
    </div>
  </div>
  <div class="exam-room" style="align-items: center; justify-content: center; color: rgba(255,255,255,0.5);" v-else>
    <p>暂无题目，请返回首页开始测试。</p>
    <a-button type="primary" @click="$router.push('/')">返回首页</a-button>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onUnmounted } from 'vue'
import { useRouter } from 'vue-router'
import { CloseOutlined, CheckCircleFilled } from '@ant-design/icons-vue'
import { useExamStore } from '@/stores/exam'
import { useMediaRecorder } from '@/composables/useMediaRecorder'
import { useCountdown } from '@/composables/useCountdown'
import { useNetworkStatus } from '@/composables/useNetworkStatus'
import { completeExam } from '@/api/exam'
import { EXAM_STATUS, getGrade } from '@/utils/constants'
import VideoPreview from '@/components/recording/VideoPreview.vue'
import AudioWaveform from '@/components/recording/AudioWaveform.vue'
import CountdownTimer from '@/components/common/CountdownTimer.vue'
import RecordingControl from '@/components/recording/RecordingControl.vue'
import ScoreRing from '@/components/common/ScoreRing.vue'
import QuestionMetaTags from '@/components/common/QuestionMetaTags.vue'
import QuestionRichContent from '@/components/common/QuestionRichContent.vue'
import { message } from 'ant-design-vue'

const router = useRouter()
const examStore = useExamStore()
const recorder = useMediaRecorder()
const { isOnline } = useNetworkStatus()
const stream = recorder.stream
const recorderDuration = recorder.duration
const countdown = useCountdown(0)

const elapsed = ref(0)
let elapsedTimer = null

const formattedElapsed = computed(() => {
  const m = Math.floor(elapsed.value / 60)
  const s = elapsed.value % 60
  return `${String(m).padStart(2, '0')}:${String(s).padStart(2, '0')}`
})

const gradeLabel = computed(() => {
  if (!examStore.scoringResult) return ''
  return getGrade(examStore.scoringResult.totalScore, examStore.scoringResult.maxScore).label
})

onMounted(async () => {
  await new Promise((resolve) => setTimeout(resolve, 300))
  const currentStream = await recorder.initStream({ videoEnabled: examStore.videoEnabled })
  if (!currentStream) {
    await new Promise((resolve) => setTimeout(resolve, 500))
    await recorder.initStream({ videoEnabled: examStore.videoEnabled })
  }
  if (examStore.mockMode && examStore.examStartTime) {
    elapsedTimer = setInterval(() => {
      elapsed.value = Math.floor((Date.now() - examStore.examStartTime) / 1000)
    }, 1000)
  }
  if (examStore.currentQuestion && examStore.status === EXAM_STATUS.IDLE && examStore.mockMode) {
    onStartPrep()
  }
})

onUnmounted(() => {
  recorder.destroyStream()
  countdown.stop()
  clearInterval(elapsedTimer)
  if (examStore.mockMode) {
    examStore.examElapsed = elapsed.value
  }
})

function onStartPrep() {
  const q = examStore.currentQuestion
  examStore.startPreparing()
  countdown.reset(q.prepTime || 90)
  countdown.onFinish(() => {
    onStartAnswer()
  })
  countdown.start()
}

function onStartAnswer() {
  countdown.stop()
  examStore.startAnswering()
  recorder.startRecording()
  const q = examStore.currentQuestion
  countdown.reset(q.answerTime || 180)
  countdown.onFinish(() => {
    onSubmit()
  })
  countdown.start()
}

async function onSubmit() {
  countdown.stop()
  try {
    const blob = await recorder.stopRecording()
    if (blob) {
      await examStore.submitAnswer(blob)
    }
  } catch (error) {
    message.error(`提交失败: ${error.message || '未知错误'}`)
  }
}

function onNext() {
  examStore.nextQuestion()
  countdown.reset(0)
  if (examStore.mockMode) {
    setTimeout(() => onStartPrep(), 500)
  }
}

async function onFinish() {
  const examId = examStore.examId
  if (!examId) {
    message.error('考试数据异常，返回首页')
    router.push('/')
    return
  }
  try {
    await completeExam(examId)
  } catch (error) {
    console.error('保存历史记录失败:', error)
  }
  countdown.stop()
  recorder.destroyStream()
  router.push(`/result/${examId}`)
}

async function exitExam() {
  countdown.stop()
  recorder.destroyStream()
  const examId = examStore.examId
  if (examId && examStore.answers.length > 0) {
    try {
      await completeExam(examId)
      message.success('练习记录已保存')
    } catch (error) {
      console.error('保存记录失败:', error)
    }
  }
  examStore.exitExam()
  router.push('/')
}
</script>

<style lang="less" scoped>
@import '@/styles/exam-room.less';

.question-stem {
  margin-top: 10px;
}

.question-stem :deep(.question-rich-content__body) {
  color: rgba(255, 255, 255, 0.9);
}

.brief-score {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 12px;
  padding: 8px 16px;
}

.brief-score__label {
  font-size: 18px;
  font-weight: 600;
  color: #fff;
}

.exam-room__brief-result {
  flex-shrink: 0;
}

.exam-room__total-timer {
  background: rgba(255, 255, 255, 0.15);
  padding: 2px 10px;
  border-radius: 12px;
  font-size: 13px;
  color: rgba(255, 255, 255, 0.85);
  font-variant-numeric: tabular-nums;
}

.exam-room__offline-banner {
  background: #fff1f0;
  color: #cf1322;
  text-align: center;
  padding: 8px 16px;
  font-size: 13px;
  font-weight: 500;
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  z-index: 1000;
  animation: slideDown 0.3s ease;
}

@keyframes slideDown {
  from { transform: translateY(-100%); }
  to { transform: translateY(0); }
}
</style>
