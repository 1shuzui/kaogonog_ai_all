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
      <div class="exam-room__header-actions">
        <a-button type="text" size="small" style="color: rgba(255,255,255,0.8)" @click="handleBack">
          返回
        </a-button>
        <a-popconfirm title="确定退出考试？已答题目不会丢失。" @confirm="exitExam">
          <a-button type="text" size="small" style="color: rgba(255,255,255,0.8)">
            <CloseOutlined /> 退出
          </a-button>
        </a-popconfirm>
      </div>
    </div>

    <!-- 主内容区：题目 + 视频 -->
    <div class="exam-room__main">
      <!-- 题目卡片 -->
      <div class="exam-room__question">
        <a-tag color="blue" style="margin-bottom: 8px">
          {{ dimensionName }}
        </a-tag>
        <div class="question-stem">{{ examStore.currentQuestion.stem }}</div>
      </div>
    </div>

    <!-- 摄像头预览（始终浮动，准备阶段大一点，答题阶段小窗） -->
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
      <!-- 准备阶段提示 -->
      <div v-if="examStore.status === 'preparing'" class="camera-hint">
        准备时间，请思考作答思路
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
      <div v-else-if="examStore.status === 'submitting'" class="exam-room__submitting">
        <a-progress
          :percent="examStore.submitProgressPercent"
          status="active"
          :show-info="false"
          stroke-color="#1B5FAA"
        />
        <span>{{ examStore.submitStepText }}</span>
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

    <div v-if="examStore.status === 'answering'" class="exam-room__text-entry">
      <a-space wrap>
        <a-button ghost @click="openTextAnswerModal">文字作答 / 上传 txt</a-button>
        <a-upload
          accept=".mp3,.wav,.m4a,.mp4,.avi,.mov,.mkv,.webm,audio/*,video/*"
          :show-upload-list="false"
          :before-upload="handleMediaBeforeUpload"
        >
          <a-button ghost>上传音频 / 视频</a-button>
        </a-upload>
        <a-button v-if="uploadedMediaName" type="primary" ghost @click="submitUploadedMedia">
          提交上传媒体
        </a-button>
        <a-button v-if="hasPendingFiles" ghost @click="fileListVisible = true">
          当前文件
        </a-button>
      </a-space>
      <span class="exam-room__text-entry-hint">不录音也可直接提交文字答案，或上传已有音视频文件。</span>
      <div v-if="hasPendingFiles" class="exam-room__pending-files">
        <div class="exam-room__pending-files-title">当前待提交文件</div>
        <div v-for="item in pendingFileItems" :key="item.key" class="exam-room__pending-file">
          <div class="exam-room__pending-file-main">
            <span class="exam-room__pending-file-type">{{ item.type }}</span>
            <span class="exam-room__pending-file-name">{{ item.name }}</span>
          </div>
          <a-button type="link" size="small" @click="item.remove">
            移除
          </a-button>
        </div>
      </div>
    </div>

    <a-modal
      v-model:open="textAnswerVisible"
      title="文字作答 / 上传 txt"
      ok-text="提交文字答案"
      cancel-text="取消"
      :confirm-loading="textSubmitting"
      @ok="submitTextAnswer"
    >
      <a-textarea
        v-model:value="textAnswer"
        :rows="8"
        :maxlength="5000"
        show-count
        placeholder="请输入作答内容，或上传 .txt 文件后再提交。"
      />
      <div class="exam-room__text-upload">
        <a-upload
          accept=".txt"
          :show-upload-list="false"
          :before-upload="handleTxtBeforeUpload"
        >
          <a-button style="margin-top: 12px">上传 txt</a-button>
        </a-upload>
        <span v-if="textFileName" class="exam-room__text-upload-name">{{ textFileName }}</span>
      </div>
    </a-modal>

    <a-modal
      v-model:open="fileListVisible"
      title="当前待提交文件"
      :footer="null"
    >
      <div v-if="hasPendingFiles" class="exam-room__pending-files-modal">
        <div v-for="item in pendingFileItems" :key="`${item.key}_modal`" class="exam-room__pending-file">
          <div class="exam-room__pending-file-main">
            <span class="exam-room__pending-file-type">{{ item.type }}</span>
            <span class="exam-room__pending-file-name">{{ item.name }}</span>
          </div>
          <a-button type="link" size="small" @click="item.remove">
            移除
          </a-button>
        </div>
      </div>
      <a-empty v-else description="当前没有待提交文件" />
    </a-modal>
  </div>
  <div v-else class="exam-room" style="align-items: center; justify-content: center; color: rgba(255,255,255,0.5);">
    <p>暂无题目，请返回首页开始测评</p>
    <a-button type="primary" @click="$router.push('/')">返回首页</a-button>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onUnmounted } from 'vue'
import { useRouter } from 'vue-router'
import { CloseOutlined, CheckCircleFilled } from '@ant-design/icons-vue'
import { useExamStore } from '@/stores/exam'
import { useMediaRecorder } from '@/composables/useMediaRecorder'
import { useSpeechRecognition } from '@/composables/useSpeechRecognition'
import { useCountdown } from '@/composables/useCountdown'
import { useNetworkStatus } from '@/composables/useNetworkStatus'
import { completeExam } from '@/api/exam'
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
const speechRecognition = useSpeechRecognition()
const { isOnline } = useNetworkStatus()
const stream = recorder.stream
const recorderDuration = recorder.duration
const countdown = useCountdown(0)

// 模拟面试全程计时
const elapsed = ref(0)
let elapsedTimer = null
const completionSaving = ref(false)
const textAnswerVisible = ref(false)
const textSubmitting = ref(false)
const textAnswer = ref('')
const textFileName = ref('')
const fileListVisible = ref(false)
const uploadedMediaBlob = ref(null)
const uploadedMediaName = ref('')
const uploadedMediaType = ref('')

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

const hasPendingFiles = computed(() => !!(textFileName.value || uploadedMediaName.value))

const pendingFileItems = computed(() => {
  const items = []
  if (textFileName.value) {
    items.push({
      key: 'text',
      type: 'TXT',
      name: textFileName.value,
      remove: clearTextSelection
    })
  }
  if (uploadedMediaName.value) {
    items.push({
      key: 'media',
      type: uploadedMediaType.value?.startsWith('video/') ? '视频' : '音频/视频',
      name: uploadedMediaName.value,
      remove: clearUploadedMediaSelection
    })
  }
  return items
})

onMounted(async () => {
  // 等待上一页面释放摄像头后再初始化，避免设备占用冲突
  await new Promise(r => setTimeout(r, 300))
  const s = await recorder.initStream({ videoEnabled: examStore.videoEnabled })
  if (!s) {
    // 首次失败，等待后重试一次
    await new Promise(r => setTimeout(r, 500))
    await recorder.initStream({ videoEnabled: examStore.videoEnabled })
  }
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
  speechRecognition.stop().catch(() => {})
  countdown.stop()
  clearInterval(elapsedTimer)
  if (examStore.mockMode) {
    examStore.syncExamElapsed(elapsed.value)
  }
})

function onStartPrep() {
  const q = examStore.currentQuestion
  speechRecognition.reset()
  resetTextAnswerState()
  resetUploadedMediaState()
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
  speechRecognition.reset()
  speechRecognition.start()
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
  const remainingSeconds = Math.max(0, Number(countdown.remaining.value) || 0)
  countdown.stop()
  try {
    const blob = await recorder.stopRecording()
    const transcriptOverride = await speechRecognition.stop()
    if (!blob && !String(transcriptOverride || '').trim()) {
      throw new Error('未获取到有效作答内容，请重新开始本题或改用文字作答')
    }
    await examStore.submitAnswer(blob, {
      transcriptOverride,
      skipUpload: !blob && !!String(transcriptOverride || '').trim()
    })
  } catch (e) {
    await restoreAnswerAfterFailure(remainingSeconds, { restartCapture: true })
    const errorMessage = e?.response?.data?.detail || e?.message || '未知错误'
    message.error(`提交失败：${errorMessage}。可直接改用文字作答 / 上传 txt / 上传音视频文件`)
  }
}

function onNext() {
  resetTextAnswerState()
  resetUploadedMediaState()
  examStore.nextQuestion()
  countdown.reset(0)
  if (examStore.mockMode) {
    // 模拟面试自动开始下一题准备
    setTimeout(() => onStartPrep(), 500)
  }
}

async function onFinish() {
  if (completionSaving.value) return
  const examId = examStore.examId
  if (!examId) {
    message.error('考试数据异常，返回首页')
    router.push('/')
    return
  }
  // 调用完成考试接口，保存历史记录
  try {
    completionSaving.value = true
    await completeExam(examId)
  } catch (e) {
    console.error('保存历史记录失败:', e)
    message.warning('结果页可查看，但历史完成状态写回失败，请稍后重试')
  } finally {
    completionSaving.value = false
  }
  countdown.stop()
  recorder.destroyStream()
  router.push(`/result/${examId}`)
}

async function exitExam() {
  if (completionSaving.value) return
  countdown.stop()
  recorder.destroyStream()
  const examId = examStore.examId
  let shouldClearSession = true
  // 如果已经有答题记录，保存后再退出
  if (examId && examStore.answers.length > 0) {
    try {
      completionSaving.value = true
      await completeExam(examId)
      message.success('练习记录已保存')
    } catch (e) {
      console.error('保存记录失败:', e)
      shouldClearSession = false
      examStore.syncExamElapsed(elapsed.value)
      message.warning('历史完成状态未写回，可在首页继续恢复本次练习')
    } finally {
      completionSaving.value = false
    }
  }
  if (shouldClearSession) {
    examStore.exitExam()
  }
  router.push('/')
}

function handleBack() {
  if (examStore.answers.length === 0 && examStore.status !== EXAM_STATUS.SUBMITTING) {
    countdown.stop()
    recorder.destroyStream()
    router.back()
    return
  }
  void exitExam()
}

function resetTextAnswerState() {
  textAnswerVisible.value = false
  textSubmitting.value = false
  textAnswer.value = ''
  textFileName.value = ''
  fileListVisible.value = false
}

function resetUploadedMediaState() {
  uploadedMediaBlob.value = null
  uploadedMediaName.value = ''
  uploadedMediaType.value = ''
  if (!textFileName.value) {
    fileListVisible.value = false
  }
}

function clearTextSelection() {
  textAnswer.value = ''
  textFileName.value = ''
  if (!uploadedMediaName.value) {
    fileListVisible.value = false
  }
}

function clearUploadedMediaSelection() {
  uploadedMediaBlob.value = null
  uploadedMediaName.value = ''
  uploadedMediaType.value = ''
  if (!textFileName.value) {
    fileListVisible.value = false
  }
}

async function restoreAnswerAfterFailure(remainingSeconds, options = {}) {
  examStore.status = EXAM_STATUS.ANSWERING
  examStore.submitStep = ''
  examStore.persistSession()

  const safeRemaining = Math.max(0, Number(remainingSeconds) || 0)
  if (safeRemaining > 0) {
    countdown.reset(safeRemaining)
    countdown.onFinish(() => {
      onSubmit()
    })
    countdown.start()
  }

  if (options.restartCapture) {
    if (!recorder.isRecording.value) {
      recorder.startRecording()
    }
    if (!speechRecognition.active.value) {
      speechRecognition.start()
    }
  }
}

function openTextAnswerModal() {
  textAnswerVisible.value = true
}

async function handleTxtBeforeUpload(file) {
  try {
    textAnswer.value = String(await file.text()).trim()
    textFileName.value = file.name
    message.success(`已载入 ${file.name}`)
  } catch (e) {
    message.error(e?.message || '读取 txt 文件失败')
  }
  return false
}

async function handleMediaBeforeUpload(file) {
  uploadedMediaBlob.value = file
  uploadedMediaName.value = file.name
  uploadedMediaType.value = file.type || ''
  message.success(`已载入 ${file.name}`)
  return false
}

async function submitUploadedMedia() {
  if (!uploadedMediaBlob.value) {
    message.warning('请先选择音频或视频文件')
    return
  }

  const remainingSeconds = Math.max(0, Number(countdown.remaining.value) || 0)
  countdown.stop()
  try {
    await recorder.stopRecording()
    await speechRecognition.stop()
    await examStore.submitAnswer(uploadedMediaBlob.value, {
      mediaFileName: uploadedMediaName.value,
      mediaMimeType: uploadedMediaType.value,
      mediaSource: 'uploaded_file'
    })
    resetUploadedMediaState()
  } catch (e) {
    await restoreAnswerAfterFailure(remainingSeconds)
    const errorMessage = e?.response?.data?.detail || e?.message || '未知错误'
    message.error(`上传媒体提交失败：${errorMessage}`)
  }
}

async function submitTextAnswer() {
  const transcript = String(textAnswer.value || '').trim()
  if (!transcript) {
    message.warning('请先输入文字答案或上传 txt 文件')
    return
  }

  const remainingSeconds = Math.max(0, Number(countdown.remaining.value) || 0)
  countdown.stop()
  textSubmitting.value = true
  try {
    await recorder.stopRecording()
    await speechRecognition.stop()
    await examStore.submitAnswer(null, {
      transcriptOverride: transcript,
      skipUpload: true
    })
    textAnswerVisible.value = false
  } catch (e) {
    await restoreAnswerAfterFailure(remainingSeconds)
    textAnswerVisible.value = true
    const errorMessage = e?.response?.data?.detail || e?.message || '未知错误'
    message.error(`文字提交失败：${errorMessage}`)
  } finally {
    textSubmitting.value = false
  }
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

.exam-room__text-entry {
  display: flex;
  justify-content: center;
  gap: 12px;
  flex-wrap: wrap;
  flex-direction: column;
}

.exam-room__text-entry-hint {
  color: rgba(255, 255, 255, 0.7);
  font-size: 12px;
}

.exam-room__pending-files {
  width: min(100%, 560px);
  padding: 12px 14px;
  border-radius: 12px;
  background: rgba(255, 255, 255, 0.14);
  border: 1px solid rgba(255, 255, 255, 0.18);
}

.exam-room__pending-files-title {
  color: rgba(255, 255, 255, 0.92);
  font-size: 13px;
  font-weight: 600;
  margin-bottom: 8px;
}

.exam-room__pending-files-modal {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.exam-room__pending-file {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
}

.exam-room__pending-file-main {
  min-width: 0;
  display: flex;
  align-items: center;
  gap: 10px;
}

.exam-room__pending-file-type {
  flex-shrink: 0;
  padding: 2px 8px;
  border-radius: 999px;
  background: rgba(255, 255, 255, 0.2);
  color: #fff;
  font-size: 12px;
}

.exam-room__pending-file-name {
  color: rgba(255, 255, 255, 0.92);
  word-break: break-all;
}

.exam-room__header-actions {
  display: flex;
  align-items: center;
  gap: 4px;
}

.exam-room__submitting {
  width: min(320px, 80vw);
  color: rgba(255, 255, 255, 0.82);
}

.exam-room__submitting span {
  display: inline-block;
  margin-top: 8px;
}

.exam-room__text-upload {
  display: flex;
  align-items: center;
  gap: 12px;
  flex-wrap: wrap;
}

.exam-room__text-upload-name {
  margin-top: 12px;
  color: rgba(0, 0, 0, 0.65);
  font-size: 12px;
}

@keyframes slideDown {
  from { transform: translateY(-100%); }
  to { transform: translateY(0); }
}
</style>
