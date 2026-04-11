<template>
  <div class="exam-room" v-if="examStore.currentQuestion">
    <!-- 离线提示 -->
    <div v-if="!isOnline" class="exam-room__offline-banner">
      ⚠️ 网络已断开，请检查网络连接。录音数据已暂存，恢复网络后可继续提交。
    </div>

    <!-- 顶部状态栏 -->
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

    <!-- 主内容区：题目 + 视频小窗 -->
    <div class="exam-room__main">
      <!-- 题目卡片 -->
      <div class="exam-room__question">
        <a-tag color="blue" style="margin-bottom: 8px">
          {{ dimensionName }}
        </a-tag>
        <div class="question-stem">{{ examStore.currentQuestion.stem }}</div>
      </div>

      <!-- 视频预览（准备阶段大预览，答题阶段小窗） -->
      <div 
        class="exam-room__video-container"
        :class="{ 'is-pip': examStore.status === 'answering' || examStore.status === 'submitting' || examStore.status === 'completed' }"
      >
        <VideoPreview
          :stream="stream"
          :recording="examStore.status === 'answering'"
          :duration="recorderDuration"
        />
        <!-- 准备阶段提示 -->
        <div v-if="examStore.status === 'preparing'" class="video-hint">
          准备时间，请思考作答思路
        </div>
      </div>
    </div>

    <!-- 倒计时 -->
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

    <!-- 音频波形 -->
    <div class="exam-room__waveform" v-show="examStore.status === 'answering'">
      <AudioWaveform
        :stream="stream"
        :active="examStore.status === 'answering'"
        :width="320"
        :height="60"
      />
    </div>

    <!-- 简要评分结果 (答题完成后) -->
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

    <!-- 控制按钮 -->
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
  <div v-else class="exam-room" style="align-items: center; justify-content: center; color: rgba(255,255,255,0.5);">
    <p>暂无题目，请返回首页开始测评</p>
    <a-button type="primary" @click="$router.push('/')">返回首页</a-button>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onUnmounted, watch } from 'vue'
import { useRouter } from 'vue-router'
import { CloseOutlined, CheckCircleFilled } from '@ant-design/icons-vue'
import { useExamStore } from '@/stores/exam'
import { useMediaRecorder } from '@/composables/useMediaRecorder'
import { useCountdown } from '@/composables/useCountdown'
import { useNetworkStatus } from '@/composables/useNetworkStatus'
import { DIMENSIONS, EXAM_STATUS, getGrade } from '@/utils/constants'
import VideoPreview from '@/components/recording/VideoPreview.vue'
import AudioWaveform from '@/components/recording/AudioWaveform.vue'
import CountdownTimer from '@/components/common/CountdownTimer.vue'
import RecordingControl from '@/components/recording/RecordingControl.vue'
import ScoreRing from '@/components/common/ScoreRing.vue'
import { message } from 'ant-design-vue'

const router = useRouter()
const examStore = useExamStore()
const recorder = useMediaRecorder()
const { isOnline } = useNetworkStatus()
const stream = recorder.stream
const recorderDuration = recorder.duration
const countdown = useCountdown(0)

// 模拟面试全程计时
const elapsed = ref(0)
let elapsedTimer = null

const formattedElapsed = computed(() => {
  const m = Math.floor(elapsed.value / 60)
  const s = elapsed.value % 60
  return `${String(m).padStart(2, '0')}:${String(s).padStart(2, '0')}`
})

const dimensionName = computed(() => {
  const q = examStore.currentQuestion
  if (!q) return ''
  const dim = DIMENSIONS.find(d => d.key === q.dimension)
  return dim ? dim.name : q.dimension
})

const gradeLabel = computed(() => {
  if (!examStore.scoringResult) return ''
  return getGrade(examStore.scoringResult.totalScore, examStore.scoringResult.maxScore).label
})

onMounted(async () => {
  await recorder.initStream()
  if (examStore.mockMode && examStore.examStartTime) {
    elapsedTimer = setInterval(() => {
      elapsed.value = Math.floor((Date.now() - examStore.examStartTime) / 1000)
    }, 1000)
  }
  if (examStore.currentQuestion && examStore.status === EXAM_STATUS.IDLE) {
    if (examStore.mockMode) {
      // 模拟面试自动开始准备
      onStartPrep()
    }
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
    // 准备时间到，自动开始作答
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
    // 时间到，自动提交
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
  } catch (e) {
    message.error('提交失败: ' + (e.message || '未知错误'))
  }
}

function onNext() {
  examStore.nextQuestion()
  countdown.reset(0)
  if (examStore.mockMode) {
    // 模拟面试自动开始下一题准备
    setTimeout(() => onStartPrep(), 500)
  }
}

function onFinish() {
  const examId = examStore.examId
  if (!examId) {
    message.error('考试数据异常，返回首页')
    router.push('/')
    return
  }
  router.push(`/result/${examId}`)
}

function exitExam() {
  countdown.stop()
  recorder.destroyStream()
  examStore.exitExam()
  router.push('/')
}
</script>

<style lang="less" scoped>
@import '@/styles/exam-room.less';

.question-stem {
  font-size: 15px;
  line-height: 1.7;
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
