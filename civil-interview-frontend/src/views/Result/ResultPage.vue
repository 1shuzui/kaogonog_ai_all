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
        <!-- PDF 导出内容区 -->
        <div ref="pdfContentRef">
        <!-- 模型评测结果 -->
        <div class="result-page__model-score card">
          <div class="model-score__header">
            <div class="model-score__heading">
              <h4 class="section-title model-score__title">模型评测结果</h4>
              <p class="model-score__subtitle">{{ currentQuestionLabel }}</p>
            </div>
            <a-tag :color="gradeInfo.color" class="model-score__grade">
              {{ gradeInfo.label }}
            </a-tag>
          </div>

          <div class="model-score__metrics">
            <div class="model-score__primary">
              <span class="model-score__label">本题得分</span>
              <div class="model-score__value">
                <strong>{{ displayQuestionScore }}</strong>
                <span>/ {{ displayQuestionMaxScore }} 分</span>
              </div>
            </div>
            <div class="model-score__metric">
              <span>百分制</span>
              <strong>{{ displayTotalScore }} / {{ displayMaxScore }}</strong>
            </div>
            <div class="model-score__metric" v-if="scoringModeLabel">
              <span>评分方式</span>
              <strong>{{ scoringModeLabel }}</strong>
            </div>
          </div>

          <p v-if="result.aiComment" class="model-score__comment">{{ result.aiComment }}</p>
        </div>

        <!-- 多题切换 -->
        <div v-if="answerList.length > 1" class="answer-tabs card" data-html2canvas-ignore>
          <a-radio-group v-model:value="currentAnswerIdx" button-style="solid" size="small">
            <a-radio-button v-for="(ans, idx) in answerList" :key="idx" :value="idx">
              第 {{ idx + 1 }} 题
              <span :style="{ color: ansScoreColor(ans), marginLeft: '4px' }">
                {{ formatAnswerScore(ans) }}
              </span>
            </a-radio-button>
          </a-radio-group>
        </div>

        <!-- 总分区域 -->
        <div class="result-page__score card">
          <h4 class="section-title">百分制总览</h4>
          <ScoreRing :score="result.totalScore" :maxScore="result.maxScore" size="large" />
        </div>

        <!-- 雷达图 -->
        <div class="card" style="margin-top: 12px">
          <h4 class="section-title">能力维度分析</h4>
          <RadarChart :dimensions="result.dimensions" size="medium" />
        </div>

        <!-- 失分诊断 -->
        <div style="margin-top: 12px">
          <LossAnalysis :dimensions="result.dimensions" />
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
import { getGrade } from '@/utils/constants'
import { getHistoryDetail } from '@/api/history'
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
const activeExamId = computed(() => String(examStore.examId || route.params.examId || ''))

function toFiniteNumber(value, fallback = 0) {
  const number = Number(value)
  return Number.isFinite(number) ? number : fallback
}

function formatScoreNumber(value) {
  const number = toFiniteNumber(value)
  return Number.isInteger(number) ? String(number) : number.toFixed(2).replace(/\.?0+$/, '')
}

function getAnswerScorePair(answer) {
  const scoring = answer?.scoringResult || {}
  const questionMaxScore = toFiniteNumber(scoring.questionMaxScore, 0)
  const maxScore = questionMaxScore > 0
    ? questionMaxScore
    : toFiniteNumber(scoring.maxScore, 100)
  const questionScore = scoring.questionScore !== undefined && scoring.questionScore !== null
    ? toFiniteNumber(scoring.questionScore, 0)
    : toFiniteNumber(scoring.totalScore, 0)

  return {
    score: questionScore,
    maxScore: maxScore > 0 ? maxScore : 100
  }
}

function formatAnswerScore(answer) {
  const { score } = getAnswerScorePair(answer)
  return `${formatScoreNumber(score)}分`
}

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

const currentQuestionLabel = computed(() => {
  const indexText = answerList.value.length > 1 ? `第 ${currentAnswerIdx.value + 1} 题` : '本题'
  const stem = currentAnswer.value?.questionStem || ''
  return stem ? `${indexText}：${stem}` : indexText
})

const currentScorePair = computed(() => getAnswerScorePair({ scoringResult: result.value }))

const displayQuestionScore = computed(() => formatScoreNumber(currentScorePair.value.score))
const displayQuestionMaxScore = computed(() => formatScoreNumber(currentScorePair.value.maxScore))
const displayTotalScore = computed(() => formatScoreNumber(result.value?.totalScore || 0))
const displayMaxScore = computed(() => formatScoreNumber(result.value?.maxScore || 100))

const scoringModeLabel = computed(() => {
  const mode = String(result.value?.scoringMode || '').trim()
  const labels = {
    llm: '模型评分',
    rule_based: '规则兜底',
    screened_zero: '无效作答筛查',
    conservative: '保守评分'
  }
  return labels[mode] || mode
})

const currentMediaUrl = computed(() => {
  const blobUrl = blobUrls.value[currentAnswerIdx.value]
  if (blobUrl) return blobUrl
  return normalizeMediaUrl(answerList.value[currentAnswerIdx.value]?.mediaUrl)
})

const currentMediaType = computed(() => {
  const ans = answerList.value[currentAnswerIdx.value]
  return String(ans?.recordingBlob?.type || ans?.mediaType || '')
})

const currentRecordingUrl = computed(() => {
  if (!currentMediaUrl.value) return ''
  if (currentMediaType.value.includes('video')) return ''
  return currentMediaUrl.value
})

const currentVideoUrl = computed(() => {
  if (!currentMediaUrl.value) return ''
  if (currentMediaType.value.includes('video')) return currentMediaUrl.value
  return ''
})

function ansScoreColor(ans) {
  const { score, maxScore } = getAnswerScorePair(ans)
  const ratio = score / maxScore
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
  syncDisplayedAnswer(answerList.value[idx])
})

const isStarred = computed(() => {
  const ans = answerList.value[currentAnswerIdx.value]
  if (!ans) return false
  return favoritesStore.isFavorited(activeExamId.value, ans.questionId)
})

function toggleFavorite() {
  const ans = answerList.value[currentAnswerIdx.value]
  if (!ans || !ans.questionId || !result.value || !activeExamId.value) return
  const q = examStore.questionList?.find(q => q.id === ans.questionId)
  if (isStarred.value) {
    const item = favoritesStore.items.find(i => i.examId === activeExamId.value && i.questionId === ans.questionId)
    if (item) favoritesStore.removeItem(item.id)
  } else {
    favoritesStore.addItem({
      examId: activeExamId.value,
      questionId: ans.questionId,
      questionStem: q?.stem || ans.questionStem || '',
      dimension: q?.dimension || ans.dimension || '',
      score: result.value.totalScore,
      maxScore: result.value.maxScore,
      grade: gradeInfo.value.label,
      type: 'starred'
    })
  }
}

function autoAddWeakAll() {
  if (!activeExamId.value) return
  for (const ans of answerList.value) {
    if (!ans.scoringResult || !ans.questionId) continue
    const ratio = ans.scoringResult.totalScore / ans.scoringResult.maxScore
    if (ratio < 0.6) {
      const q = examStore.questionList?.find(q => q.id === ans.questionId)
      favoritesStore.addItem({
        examId: activeExamId.value,
        questionId: ans.questionId,
        questionStem: q?.stem || ans.questionStem || '',
        dimension: q?.dimension || ans.dimension || '',
        score: ans.scoringResult.totalScore,
        maxScore: ans.scoringResult.maxScore,
        grade: getGrade(ans.scoringResult.totalScore, ans.scoringResult.maxScore).label,
        type: 'weak'
      })
    }
  }
}

function normalizeMediaUrl(url) {
  const value = String(url || '').trim()
  if (!value) return ''
  if (value.startsWith('blob:') || value.startsWith('http://') || value.startsWith('https://') || value.startsWith('/')) {
    return value
  }
  return `/${value}`
}

function syncDisplayedAnswer(answer) {
  if (!answer) return
  result.value = answer.scoringResult || null
  transcript.value = answer.transcript || ''
}

function syncAnswerList(answers) {
  const normalizedAnswers = (answers || []).filter((answer) => answer?.scoringResult)
  answerList.value = normalizedAnswers
  currentAnswerIdx.value = 0
  blobUrls.value = normalizedAnswers.map((answer) => {
    if (answer.recordingBlob) {
      return URL.createObjectURL(answer.recordingBlob)
    }
    return ''
  })

  if (!normalizedAnswers.length) {
    return false
  }

  syncDisplayedAnswer(normalizedAnswers[0])
  autoAddWeakAll()
  return true
}

onMounted(async () => {
  // 从 store 获取所有答题记录
  if (examStore.answers.length > 0) {
    syncAnswerList(examStore.answers)
    loading.value = false
    return
  }

  // 单题模式（从当前 scoringResult）
  if (examStore.scoringResult) {
    syncAnswerList([{
      questionId: examStore.currentQuestion?.id,
      recordingBlob: examStore.recordingBlob,
      transcript: examStore.transcript,
      scoringResult: examStore.scoringResult
    }])
    loading.value = false
    return
  }

  // 从历史详情 API 回填
  try {
    const examId = String(route.params.examId || '')
    const detail = await getHistoryDetail(examId)
    const answers = Array.isArray(detail?.answers) ? detail.answers : []

    if (!syncAnswerList(answers)) {
      result.value = {
        totalScore: detail?.totalScore || 0,
        maxScore: detail?.maxScore || 100,
        grade: detail?.grade || '',
        dimensions: detail?.dimensions || [],
        aiComment: detail?.questionSummary || '历史练习记录',
      }
      transcript.value = ''
    }
  } catch (e) {
    // ignore
  } finally {
    loading.value = false
  }
})

onUnmounted(() => {
  blobUrls.value.forEach(url => {
    if (url?.startsWith('blob:')) URL.revokeObjectURL(url)
  })
})
</script>

<style lang="less" scoped>
@import '@/styles/variables.less';

.result-page__score {
  text-align: center;
  padding: 24px 16px;
}

.result-page__model-score {
  padding: 20px;
}

.model-score__header {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 16px;
  margin-bottom: 16px;
}

.model-score__heading {
  min-width: 0;
}

.model-score__title {
  margin-bottom: 6px;
}

.model-score__subtitle {
  color: @text-secondary;
  font-size: @font-size-sm;
  line-height: 1.6;
  margin: 0;
  word-break: break-word;
}

.model-score__grade {
  flex: 0 0 auto;
  font-size: 15px;
  padding: 3px 12px;
}

.model-score__metrics {
  display: grid;
  grid-template-columns: minmax(180px, 1.3fr) repeat(2, minmax(120px, 0.7fr));
  gap: 12px;
}

.model-score__primary,
.model-score__metric {
  border: 1px solid @border-color;
  border-radius: @border-radius;
  padding: 14px 16px;
  min-width: 0;
}

.model-score__primary {
  background: fade(@primary-color, 6%);
}

.model-score__label,
.model-score__metric span {
  color: @text-secondary;
  display: block;
  font-size: @font-size-sm;
  margin-bottom: 8px;
}

.model-score__value {
  color: @text-primary;
  display: flex;
  align-items: baseline;
  gap: 6px;
  flex-wrap: wrap;
}

.model-score__value strong {
  color: @primary-color;
  font-size: 34px;
  line-height: 1;
}

.model-score__metric strong {
  color: @text-primary;
  display: block;
  font-size: @font-size-lg;
  line-height: 1.3;
  word-break: break-word;
}

.model-score__comment {
  color: @text-secondary;
  font-size: @font-size-sm;
  line-height: 1.7;
  margin: 14px 0 0;
  text-align: left;
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
  margin-top: 12px;
  margin-bottom: 12px;
  overflow-x: auto;
  white-space: nowrap;
}

.playback-controls {
  padding: 8px 0;
}

@media (max-width: 720px) {
  .model-score__header {
    display: block;
  }

  .model-score__grade {
    margin-top: 12px;
  }

  .model-score__metrics {
    grid-template-columns: 1fr;
  }
}
</style>
