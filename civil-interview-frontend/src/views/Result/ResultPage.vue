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
          <ScoreRing :score="result.totalScore" :maxScore="result.maxScore" size="large" />
          <div class="result-page__grade">
            <a-tag :color="gradeInfo.color" style="font-size: 16px; padding: 4px 16px;">
              {{ gradeInfo.label }}
            </a-tag>
            <a-tag v-if="scoringModeLabel" :color="isRuleBased ? 'orange' : 'blue'" style="font-size: 14px; padding: 4px 12px; margin-left: 8px;">
              {{ scoringModeLabel }}
            </a-tag>
          </div>
          <a-alert
            v-if="isRuleBased"
            style="margin-top: 12px; text-align: left"
            type="warning"
            show-icon
            message="当前环境未配置真实 Qwen 评分模型，本次结果为题库规则评分。"
          />
          <p class="result-page__comment">{{ result.aiComment }}</p>
        </div>

        <div class="card result-page__question-score" style="margin-top: 12px" v-if="result.questionMaxScore">
          <h4 class="section-title">单题模型判断</h4>
          <div class="result-page__question-score-value">
            {{ result.questionScore || 0 }} / {{ result.questionMaxScore }}
          </div>
          <p class="result-page__question-score-hint">
            这是按题目采分点折算后的单题分；上方总分仍保留 100 分制维度分析，便于横向比较。
          </p>
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

        <!-- 普通话与表达分析 -->
        <SpeechAnalysisPanel v-if="speechAnalysis" :analysis="speechAnalysis" />

        <div class="card result-page__visual-observation" style="margin-top: 12px" v-if="result.visualObservation">
          <h4 class="section-title">动作与表情管理</h4>
          <p class="result-page__visual-observation-text">{{ result.visualObservation }}</p>
          <a-alert
            type="info"
            show-icon
            message="该观察仅作为表达状态补充，用于辅助判断仪态稳定性、镜头表现和表情管理，不替代内容评分依据。"
          />
        </div>

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

        <!-- 语音转写结果 -->
        <div style="margin-top: 12px">
          <TranscriptViewer
            title="语音转写结果"
            :transcript="result.highlightedTranscript || transcript"
            :keywords="result.matchedKeywords"
          />
        </div>

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
import { ref, computed, watch, onUnmounted } from 'vue'
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
const routeExamId = computed(() => route.params.examId || '')
const currentExamId = computed(() => routeExamId.value || examStore.examId || '')
let loadToken = 0

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

const isRuleBased = computed(() => result.value?.scoringMode === 'rule_based')

const scoringModeLabel = computed(() => {
  if (!result.value) return ''
  if (result.value.scoringMode === 'rule_based') return '题库规则评分'
  if (result.value.scoringMode === 'llm') return 'AI模型评分'
  if (result.value.scoringMode === 'screened_zero') return '无效作答'
  return ''
})

const currentAnswer = computed(() => answerList.value[currentAnswerIdx.value] || null)

function mediaKind(ans) {
  const type = ans?.recordingBlob?.type || ans?.mediaType || ''
  const filename = ans?.mediaFilename || ''
  if (type.includes('audio')) return 'audio'
  if (type.includes('video')) return 'video'
  if (/\.(mp3|wav|m4a|ogg)$/i.test(filename)) return 'audio'
  if (/\.(mp4|avi|mov|mkv)$/i.test(filename)) return 'video'
  return ''
}

const currentMediaUrl = computed(() => {
  const blobUrl = blobUrls.value[currentAnswerIdx.value]
  if (blobUrl) return blobUrl
  return currentAnswer.value?.mediaUrl || ''
})

const currentRecordingUrl = computed(() => {
  const url = currentMediaUrl.value
  if (!url) return ''
  if (mediaKind(currentAnswer.value) === 'video') return ''
  return url
})

const currentVideoUrl = computed(() => {
  const url = currentMediaUrl.value
  if (!url) return ''
  return mediaKind(currentAnswer.value) === 'video' ? url : ''
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
  const ans = currentAnswer.value
  if (!ans?.transcript) return null
  if (!ans?.recordingBlob && !ans?.mediaUrl) return null
  const duration = ans.duration || ans.answerTime || 180
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
  return favoritesStore.isFavorited(currentExamId.value, ans.questionId)
})

function toggleFavorite() {
  const ans = answerList.value[currentAnswerIdx.value]
  if (!ans || !ans.questionId || !result.value || !currentExamId.value) return
  const q = examStore.questionList?.find(question => question.id === ans.questionId)
  const questionStem = ans.questionStem || q?.stem || ''
  const dimension = ans.dimension || q?.dimension || ''
  if (isStarred.value) {
    const item = favoritesStore.items.find(i => i.examId === currentExamId.value && i.questionId === ans.questionId)
    if (item) favoritesStore.removeItem(item.id)
  } else {
    favoritesStore.addItem({
      examId: currentExamId.value,
      questionId: ans.questionId,
      questionStem,
      dimension,
      score: result.value.totalScore,
      maxScore: result.value.maxScore,
      grade: gradeInfo.value.label,
      type: 'starred'
    })
  }
}

function autoAddWeakAll() {
  for (const ans of answerList.value) {
    if (!ans.scoringResult || !ans.questionId || !currentExamId.value) continue
    const ratio = ans.scoringResult.totalScore / ans.scoringResult.maxScore
    if (ratio < 0.6) {
      const q = examStore.questionList?.find(question => question.id === ans.questionId)
      favoritesStore.addItem({
        examId: currentExamId.value,
        questionId: ans.questionId,
        questionStem: ans.questionStem || q?.stem || '',
        dimension: ans.dimension || q?.dimension || '',
        score: ans.scoringResult.totalScore,
        maxScore: ans.scoringResult.maxScore,
        grade: getGrade(ans.scoringResult.totalScore, ans.scoringResult.maxScore).label,
        type: 'weak'
      })
    }
  }
}

function revokeBlobUrls() {
  blobUrls.value.forEach(url => {
    if (url) URL.revokeObjectURL(url)
  })
  blobUrls.value = []
}

function resetResultState() {
  revokeBlobUrls()
  currentAnswerIdx.value = 0
  answerList.value = []
  result.value = null
  transcript.value = ''
}

function hydrateAnswers(answers) {
  revokeBlobUrls()
  currentAnswerIdx.value = 0
  answerList.value = answers
  blobUrls.value = answers.map(ans => {
    if (ans.recordingBlob) return URL.createObjectURL(ans.recordingBlob)
    return ''
  })
  const first = answers[0]
  result.value = first?.scoringResult || null
  transcript.value = first?.transcript || ''
}

function normalizeScoreResult(scoreResult) {
  if (!scoreResult || typeof scoreResult !== 'object') return null
  return Object.keys(scoreResult).length > 0 ? scoreResult : null
}

function normalizeStoredAnswer(ans) {
  const question = examStore.questionList?.find(item => item.id === ans.questionId)
  return {
    ...ans,
    questionStem: ans.questionStem || question?.stem || '',
    dimension: ans.dimension || question?.dimension || '',
    mediaUrl: ans.mediaUrl || '',
    mediaType: ans.mediaType || '',
    mediaFilename: ans.mediaFilename || '',
    mediaSource: ans.mediaSource || '',
    scoringResult: normalizeScoreResult(ans.scoringResult || ans.scoreResult)
  }
}

function normalizeHistoryAnswer(ans) {
  return {
    questionId: ans.questionId,
    questionStem: ans.questionStem || '',
    dimension: ans.dimension || '',
    prepTime: ans.prepTime,
    answerTime: ans.answerTime,
    transcript: ans.transcript || '',
    scoringResult: normalizeScoreResult(ans.scoringResult || ans.scoreResult),
    recordingBlob: null,
    mediaUrl: ans.mediaUrl || '',
    mediaType: ans.mediaType || '',
    mediaFilename: ans.mediaFilename || '',
    mediaSource: ans.mediaSource || '',
    submittedAt: ans.answeredAt || ''
  }
}

async function loadResult() {
  const currentLoadToken = ++loadToken
  loading.value = true
  resetResultState()

  const canUseStoreAnswers = examStore.answers.length > 0 && (
    !routeExamId.value || (examStore.examId && examStore.examId === routeExamId.value)
  )

  // 从当前考试 store 获取所有答题记录
  if (canUseStoreAnswers) {
    if (currentLoadToken !== loadToken) return
    hydrateAnswers(examStore.answers.map(normalizeStoredAnswer))
    loading.value = false
    autoAddWeakAll()
    return
  }

  // 单题模式（从当前 scoringResult）
  if (examStore.scoringResult && (!routeExamId.value || routeExamId.value === examStore.examId)) {
    if (currentLoadToken !== loadToken) return
    hydrateAnswers([{
      questionId: examStore.currentQuestion?.id,
      questionStem: examStore.currentQuestion?.stem || '',
      dimension: examStore.currentQuestion?.dimension || '',
      recordingBlob: examStore.recordingBlob,
      transcript: examStore.transcript,
      scoringResult: examStore.scoringResult
    }])
    loading.value = false
    autoAddWeakAll()
    return
  }

  // 从历史详情恢复
  try {
    const examId = routeExamId.value
    if (!examId) {
      return
    }
    const detail = await getHistoryDetail(examId)
    if (currentLoadToken !== loadToken) return
    const restoredAnswers = (detail.answers || [])
      .map(normalizeHistoryAnswer)
      .filter(ans => ans.scoringResult)

    if (restoredAnswers.length > 0) {
      hydrateAnswers(restoredAnswers)
      autoAddWeakAll()
      return
    }

    if (detail.totalScore !== undefined) {
      const summaryResult = {
        totalScore: detail.totalScore,
        maxScore: detail.maxScore || 100,
        grade: detail.grade,
        dimensions: detail.dimensions || [],
        aiComment: '已从历史记录恢复本次测评结果'
      }
      hydrateAnswers([{
        questionId: '',
        questionStem: detail.questionSummary || '',
        dimension: '',
        transcript: '',
        scoringResult: summaryResult,
        recordingBlob: null,
        submittedAt: detail.completedAt || ''
      }])
    }
  } catch (e) {
    // ignore
  } finally {
    if (currentLoadToken === loadToken) {
      loading.value = false
    }
  }
}

watch(routeExamId, () => {
  void loadResult()
}, { immediate: true })

onUnmounted(() => {
  loadToken += 1
  revokeBlobUrls()
})
</script>

<style lang="less" scoped>
@import '@/styles/variables.less';

.result-page__score {
  text-align: center;
  padding: 24px 16px;
}

.result-page__grade {
  margin: 12px 0;
}

.result-page__comment {
  color: @text-secondary;
  font-size: @font-size-sm;
  line-height: 1.7;
  margin-top: 8px;
  text-align: left;
}

.result-page__question-score {
  text-align: center;
  padding: 18px 16px;
}

.result-page__question-score-value {
  font-size: 28px;
  font-weight: 700;
  color: @primary-color;
}

.result-page__question-score-hint {
  margin-top: 8px;
  color: @text-secondary;
  font-size: @font-size-sm;
  line-height: 1.7;
}

.result-page__visual-observation {
  padding: 18px 16px;
}

.result-page__visual-observation-text {
  color: @text-secondary;
  font-size: @font-size-sm;
  line-height: 1.8;
  margin-bottom: 12px;
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
</style>
