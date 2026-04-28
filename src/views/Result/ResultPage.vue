<template>
  <div class="result-page page-container">
    <!-- 骨架屏加载态 -->
    <div v-if="loading" class="result-skeleton">
      <div class="card" style="padding: 24px; text-align: center;">
        <a-skeleton-avatar :size="100" shape="circle" active />
        <a-skeleton :paragraph="{ rows: 2 }" active style="margin-top: 16px;" />
      </div>
      <div class="card" style="margin-top: 12px; padding: 16px;">
        <a-skeleton :paragraph="{ rows: 4 }" active />
      </div>
      <div class="card" style="margin-top: 12px; padding: 16px;">
        <a-skeleton :paragraph="{ rows: 3 }" active />
      </div>
    </div>

    <template v-else-if="result">
        <!-- 多题切换 -->
        <div v-if="answerList.length > 1" class="answer-tabs card" data-html2canvas-ignore>
          <a-radio-group v-model:value="currentAnswerIdx" button-style="solid" size="small">
            <a-radio-button v-for="(ans, idx) in answerList" :key="idx" :value="idx">
              第 {{ idx + 1 }} 题
              <span :style="{ color: ansScoreColor(ans), marginLeft: '4px' }">
                {{ ans.scoringResult?.totalScore || 0 }}分
              </span>
            </a-radio-button>
          </a-radio-group>
        </div>

        <!-- PDF 导出内容区 -->
        <div ref="pdfContentRef">
        <!-- 总分区域 -->
        <div class="result-page__score card">
          <div class="result-page__score-hero">
            <div class="result-page__score-copy">
              <div class="result-page__score-kicker">{{ currentQuestionLabel }}评分结果</div>
              <div class="result-page__score-value">
                <span class="result-page__score-number">{{ result.totalScore }}</span>
                <span class="result-page__score-unit">/ {{ result.maxScore }} 分</span>
              </div>
              <div class="result-page__score-meta">
                <span>得分率 {{ scorePercent }}%</span>
                <span class="result-page__score-meta-dot"></span>
                <span>{{ gradeInfo.label }}</span>
              </div>
              <p v-if="currentQuestionStem" class="result-page__question-stem">{{ currentQuestionStem }}</p>
            </div>
            <div class="result-page__score-side">
              <ScoreRing
                :score="result.totalScore"
                :maxScore="result.maxScore"
                size="medium"
                label="本题得分"
              />
              <div class="result-page__grade">
                <a-tag :color="gradeInfo.color" style="font-size: 14px; padding: 2px 12px;">
                  {{ gradeInfo.label }}
                </a-tag>
              </div>
            </div>
          </div>
          <p class="result-page__comment">{{ result.aiComment }}</p>
        </div>

        <!-- 雷达图 -->
        <div class="card result-page__secondary-card" style="margin-top: 12px">
          <div class="result-page__secondary-head">
            <div>
              <h4 class="result-page__secondary-title">维度表现</h4>
              <p class="result-page__secondary-hint">辅助参考，主分数以上方本题得分为准</p>
            </div>
          </div>
          <RadarChart :dimensions="result.dimensions" size="small" />
        </div>

        <!-- 失分诊断 -->
        <div style="margin-top: 12px">
          <LossAnalysis :dimensions="result.dimensions" compact />
        </div>

        <!-- 评分关键词 -->
        <div style="margin-top: 12px">
          <ScoreBreakdown :keywords="result.matchedKeywords" />
        </div>

        <!-- 答案文字稿 -->
        <div style="margin-top: 12px">
          <TranscriptViewer
            :transcript="result.highlightedTranscript || transcript"
            :keywords="result.matchedKeywords"
          />
        </div>
        </div>

        <!-- 普通话与表达分析 -->
        <SpeechAnalysisPanel v-if="speechAnalysis" :analysis="speechAnalysis" />

        <!-- 录音回放 -->
        <div class="card" style="margin-top: 12px" v-if="currentRecordingUrl" data-html2canvas-ignore>
          <h4 class="section-title">作答录音回放</h4>
          <div class="playback-controls">
            <audio :src="currentRecordingUrl" controls style="width: 100%"></audio>
          </div>
        </div>

        <!-- 视频回放 -->
        <div class="card" style="margin-top: 12px" v-if="currentVideoUrl" data-html2canvas-ignore>
          <h4 class="section-title">作答视频回放</h4>
          <video :src="currentVideoUrl" controls style="width: 100%; border-radius: 8px"></video>
        </div>

        <!-- 底部操作 -->
        <div class="result-page__actions" data-html2canvas-ignore>
          <a-button type="primary" size="large" @click="$router.push('/exam/prepare')">
            再练一题
          </a-button>
          <a-button size="large" @click="toggleFavorite">
            <StarFilled v-if="isStarred" style="color: #faad14" />
            <StarOutlined v-else />
            {{ isStarred ? '已收藏' : '收藏' }}
          </a-button>
          <a-button size="large" :loading="exporting" @click="handleExportPdf">
            <FilePdfOutlined /> 导出PDF
          </a-button>
          <a-button size="large" @click="openShareCard">
            <ShareAltOutlined /> 分享
          </a-button>
          <a-button size="large" @click="$router.push('/')">
            返回首页
          </a-button>
        </div>

        <!-- 分享卡片 -->
        <ShareCard
          ref="shareCardRef"
          :score="result.totalScore"
          :maxScore="result.maxScore"
          :dimensions="result.dimensions || []"
        />
    </template>
  </div>
</template>

<script setup>
import { ref, computed, watch, onMounted, onUnmounted } from 'vue'
import { useRoute } from 'vue-router'
import { FilePdfOutlined, StarOutlined, StarFilled, ShareAltOutlined } from '@ant-design/icons-vue'
import { useExamStore } from '@/stores/exam'
import { useFavoritesStore } from '@/stores/favorites'
import { useTrainingStore } from '@/stores/training'
import { getGrade } from '@/utils/constants'
import { getScoringResult } from '@/api/scoring'
import { usePdfExport } from '@/composables/usePdfExport'
import { analyzeSpeech } from '@/composables/useSpeechAnalysis'
import RadarChart from '@/components/common/RadarChart.vue'
import ScoreRing from '@/components/common/ScoreRing.vue'
import ShareCard from '@/components/common/ShareCard.vue'
import SpeechAnalysisPanel from '@/components/common/SpeechAnalysisPanel.vue'
import LossAnalysis from '@/components/scoring/LossAnalysis.vue'
import ScoreBreakdown from '@/components/scoring/ScoreBreakdown.vue'
import TranscriptViewer from '@/components/scoring/TranscriptViewer.vue'

const route = useRoute()
const examStore = useExamStore()
const favoritesStore = useFavoritesStore()
const trainingStore = useTrainingStore()
const loading = ref(true)
const result = ref(null)
const transcript = ref('')
const pdfContentRef = ref(null)
const shareCardRef = ref(null)
const { exporting, exportToPdf } = usePdfExport()

// 多题支持
const answerList = ref([])
const currentAnswerIdx = ref(0)
const blobUrls = ref([])

function handleExportPdf() {
  if (pdfContentRef.value) {
    const examId = route.params.examId || 'report'
    exportToPdf(pdfContentRef.value, `测评报告_${examId}`)
  }
}

function openShareCard() {
  shareCardRef.value?.open()
}

const gradeInfo = computed(() => {
  if (!result.value) return { label: '', color: '' }
  return getGrade(result.value.totalScore, result.value.maxScore)
})

const currentAnswer = computed(() => answerList.value[currentAnswerIdx.value] || null)

const currentQuestion = computed(() => {
  const answer = currentAnswer.value
  if (!answer?.questionId) return null
  return examStore.questionList?.find((item) => item.id === answer.questionId) || null
})

const currentQuestionLabel = computed(() => (
  answerList.value.length > 1 ? `第 ${currentAnswerIdx.value + 1} 题` : '本题'
))

const currentQuestionStem = computed(() => currentQuestion.value?.stem || '')

const scorePercent = computed(() => {
  const total = Number(result.value?.totalScore || 0)
  const max = Number(result.value?.maxScore || 0)
  if (!max) return 0
  return Math.round((total / max) * 100)
})

const currentRecordingUrl = computed(() => {
  const url = blobUrls.value[currentAnswerIdx.value]
  if (!url) return ''
  // 检查 blob 类型判断是音频还是视频
  const ans = answerList.value[currentAnswerIdx.value]
  if (ans?.recordingBlob?.type?.includes('video')) return ''
  return url
})

const currentVideoUrl = computed(() => {
  const url = blobUrls.value[currentAnswerIdx.value]
  if (!url) return ''
  const ans = answerList.value[currentAnswerIdx.value]
  if (ans?.recordingBlob?.type?.includes('video')) return url
  return ''
})

function ansScoreColor(ans) {
  const score = ans.scoringResult?.totalScore || 0
  const max = ans.scoringResult?.maxScore || 100
  const ratio = score / max
  if (ratio >= 0.85) return '#389E0D'
  if (ratio >= 0.75) return '#1B5FAA'
  if (ratio >= 0.6) return '#D48806'
  return '#CF1322'
}

// 语音分析
const speechAnalysis = computed(() => {
  const ans = answerList.value[currentAnswerIdx.value]
  if (!ans?.transcript) return null
  const duration = ans.duration || 180
  return analyzeSpeech(ans.transcript, duration)
})

// 切换题目时更新显示
watch(currentAnswerIdx, (idx) => {
  const ans = answerList.value[idx]
  if (ans) {
    result.value = ans.scoringResult
    transcript.value = ans.transcript || ''
  }
})

const isStarred = computed(() => {
  const ans = answerList.value[currentAnswerIdx.value]
  if (!ans) return false
  return favoritesStore.isFavorited(examStore.examId, ans.questionId)
})

function toggleFavorite() {
  const ans = answerList.value[currentAnswerIdx.value]
  if (!ans || !ans.questionId || !result.value) return
  const q = examStore.questionList?.find(q => q.id === ans.questionId)
  if (isStarred.value) {
    const item = favoritesStore.items.find(i => i.examId === examStore.examId && i.questionId === ans.questionId)
    if (item) favoritesStore.removeItem(item.id)
  } else {
    favoritesStore.addItem({
      examId: examStore.examId,
      questionId: ans.questionId,
      questionStem: q?.stem || '',
      dimension: q?.dimension || '',
      score: result.value.totalScore,
      maxScore: result.value.maxScore,
      grade: gradeInfo.value.label,
      type: 'starred'
    })
  }
}

function autoAddWeakAll() {
  for (const ans of answerList.value) {
    if (!ans.scoringResult || !ans.questionId) continue
    const ratio = ans.scoringResult.totalScore / ans.scoringResult.maxScore
    if (ratio < 0.6) {
      const q = examStore.questionList?.find(q => q.id === ans.questionId)
      favoritesStore.addItem({
        examId: examStore.examId,
        questionId: ans.questionId,
        questionStem: q?.stem || '',
        dimension: q?.dimension || '',
        score: ans.scoringResult.totalScore,
        maxScore: ans.scoringResult.maxScore,
        grade: getGrade(ans.scoringResult.totalScore, ans.scoringResult.maxScore).label,
        type: 'weak'
      })
    }
  }
}

function recordTrainingProgress() {
  const recordKey = `training-progress-recorded:${examStore.examId || route.params.examId || 'local'}`
  if (sessionStorage.getItem(recordKey)) return

  let hasRecorded = false

  for (const ans of answerList.value) {
    if (!ans?.scoringResult || !ans.questionId) continue

    const question = examStore.questionList?.find((item) => item.id === ans.questionId)
    const trainingCategoryKey = question?.trainingCategoryKey
    if (!trainingCategoryKey) continue

    trainingStore.recordTrainingResult(trainingCategoryKey, Number(ans.scoringResult.totalScore) || 0)
    hasRecorded = true
  }

  if (hasRecorded) {
    sessionStorage.setItem(recordKey, '1')
  }
}

onMounted(async () => {
  // 从 store 获取所有答题记录
  if (examStore.answers.length > 0) {
    answerList.value = examStore.answers
    // 为每个有录音的答案创建 blob URL
    blobUrls.value = examStore.answers.map(ans => {
      if (ans.recordingBlob) return URL.createObjectURL(ans.recordingBlob)
      return ''
    })
    // 显示第一题
    const first = examStore.answers[0]
    result.value = first.scoringResult
    transcript.value = first.transcript || ''
    loading.value = false
    autoAddWeakAll()
    recordTrainingProgress()
    return
  }

  // 单题模式（从当前 scoringResult）
  if (examStore.scoringResult) {
    answerList.value = [{
      questionId: examStore.currentQuestion?.id,
      recordingBlob: examStore.recordingBlob,
      transcript: examStore.transcript,
      scoringResult: examStore.scoringResult
    }]
    result.value = examStore.scoringResult
    transcript.value = examStore.transcript
    if (examStore.recordingBlob) {
      blobUrls.value = [URL.createObjectURL(examStore.recordingBlob)]
    }
    loading.value = false
    autoAddWeakAll()
    recordTrainingProgress()
    return
  }

  // 从 API 加载
  try {
    const examId = route.params.examId
    const data = await getScoringResult(examId, '')
    result.value = data
    answerList.value = [{ scoringResult: data, transcript: '' }]
  } catch (e) {
    // ignore
  } finally {
    loading.value = false
  }
})

onUnmounted(() => {
  blobUrls.value.forEach(url => {
    if (url) URL.revokeObjectURL(url)
  })
})
</script>

<style lang="less" scoped>
@import '@/styles/variables.less';

.result-page__score {
  padding: 22px 18px 18px;
}

.result-page__score-hero {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 20px;
}

.result-page__score-copy {
  flex: 1;
  min-width: 0;
}

.result-page__score-kicker {
  font-size: 13px;
  font-weight: 600;
  color: #1B5FAA;
  letter-spacing: 0.4px;
}

.result-page__score-value {
  display: flex;
  align-items: flex-end;
  gap: 10px;
  margin-top: 10px;
  line-height: 1;
}

.result-page__score-number {
  font-size: 64px;
  font-weight: 800;
  color: @text-primary;
}

.result-page__score-unit {
  font-size: @font-size-lg;
  font-weight: 600;
  color: @text-secondary;
  padding-bottom: 8px;
}

.result-page__score-meta {
  display: flex;
  align-items: center;
  gap: 10px;
  margin-top: 12px;
  font-size: @font-size-sm;
  color: @text-secondary;
}

.result-page__score-meta-dot {
  width: 4px;
  height: 4px;
  border-radius: 50%;
  background: rgba(0, 0, 0, 0.18);
}

.result-page__question-stem {
  margin: 14px 0 0;
  padding: 10px 12px;
  border-radius: 12px;
  background: rgba(27, 95, 170, 0.05);
  color: @text-regular;
  font-size: @font-size-sm;
  line-height: 1.75;
}

.result-page__score-side {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 10px;
}

.result-page__grade {
  margin: 0;
}

.result-page__comment {
  color: @text-secondary;
  font-size: @font-size-sm;
  line-height: 1.7;
  margin-top: 18px;
  text-align: left;
}

.result-page__secondary-card {
  padding: 14px 16px 10px;
}

.result-page__secondary-head {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 12px;
  margin-bottom: 4px;
}

.result-page__secondary-title {
  margin: 0;
  font-size: @font-size-base;
  color: @text-primary;
}

.result-page__secondary-hint {
  margin: 4px 0 0;
  font-size: 12px;
  color: @text-secondary;
}

.section-title {
  font-size: @font-size-lg;
  color: @text-primary;
  margin-bottom: 12px;
}

.result-page__actions {
  display: flex;
  gap: 12px;
  justify-content: center;
  flex-wrap: wrap;
  margin-top: 24px;
  padding-bottom: 24px;
}

.answer-tabs {
  padding: 12px 16px;
  margin-bottom: 12px;
  overflow-x: auto;
  white-space: nowrap;
}

.playback-controls {
  padding: 8px 0;
}

@media (max-width: 768px) {
  .result-page__score-hero {
    flex-direction: column;
    align-items: stretch;
  }

  .result-page__score-number {
    font-size: 54px;
  }

  .result-page__score-unit {
    font-size: @font-size-base;
    padding-bottom: 6px;
  }

  .result-page__score-meta {
    flex-wrap: wrap;
    gap: 8px;
  }

  .result-page__score-side {
    flex-direction: row;
    justify-content: space-between;
  }
}
</style>
