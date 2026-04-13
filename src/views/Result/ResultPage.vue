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
          </div>
          <p class="result-page__comment">{{ result.aiComment }}</p>
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
