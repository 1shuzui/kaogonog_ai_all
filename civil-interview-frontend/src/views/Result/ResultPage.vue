<!--
PC 评分结果页，负责展示总分、能力维度、扣分分析、文字稿、改进建议和历史保存结果。

这里展示的是评分后的信息，和考场页的作答状态严格分离；题目分数、能力反馈和问题诊断不能提前出现在练习中。
能力维度用于评价考生答题表现，不要用题型分类补雷达或薄弱项。

@param: 无；结果来自路由参数、exam/history store 或评分接口返回。
@return: 渲染评分结果、复盘内容、导出/分享入口和异常空态。
@raises: 不主动抛业务异常；结果缺失、接口失败或导出失败由页面提示承接。
-->
<template>
  <div class="result-page page-container">
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
      <div ref="pdfContentRef">
        <div class="result-page__score card">
          <div class="result-page__score-hero">
            <div class="result-page__score-copy">
              <div class="result-page__score-kicker">模型评测结果 · {{ currentQuestionLabel }}</div>
              <div class="result-page__score-value">
                <span class="result-page__score-number">{{ displayQuestionScore }}</span>
                <span class="result-page__score-unit">/ {{ displayQuestionMaxScore }} 分</span>
              </div>
              <div class="result-page__score-meta">
                <span>百分制 {{ displayTotalScore }}/{{ displayMaxScore }}</span>
                <span class="result-page__score-meta-dot"></span>
                <span>{{ gradeInfo.label }}</span>
                <template v-if="scoringModeLabel">
                  <span class="result-page__score-meta-dot"></span>
                  <span>{{ scoringModeLabel }}</span>
                </template>
              </div>
              <p v-if="currentQuestionStem" class="result-page__question-stem">{{ currentQuestionStem }}</p>
            </div>
            <div class="result-page__score-side">
              <ScoreRing
                :score="currentScorePair.score"
                :maxScore="currentScorePair.maxScore"
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

        <div v-if="answerList.length > 1" class="answer-tabs card" data-html2canvas-ignore>
          <div class="answer-tabs__summary">{{ answerTabsLabel }}</div>
          <a-radio-group v-model:value="currentAnswerIdx" button-style="solid" size="small">
            <a-radio-button v-for="(ans, idx) in answerList" :key="idx" :value="idx">
              第 {{ idx + 1 }} 题
              <span :style="{ color: ansScoreColor(ans), marginLeft: '4px' }">
                {{ formatAnswerScore(ans) }}
              </span>
            </a-radio-button>
          </a-radio-group>
        </div>

        <div v-if="currentScoringPoints.length" class="card result-page__assignment-card" style="margin-top: 12px">
          <div class="result-page__assignment-head">
            <div>
              <h4 class="result-page__assignment-title">本题赋分</h4>
              <p class="result-page__assignment-hint">题目总赋分 {{ formatScoreNumber(currentQuestionAssignedScore) }} 分</p>
            </div>
          </div>
          <div class="result-page__assignment-list">
            <div
              v-for="(point, index) in currentScoringPoints"
              :key="`${index}-${point.content}`"
              class="result-page__assignment-item"
            >
              <div class="result-page__assignment-index">采分点 {{ index + 1 }}</div>
              <div class="result-page__assignment-content">{{ point.content }}</div>
              <div class="result-page__assignment-score">{{ formatScoreNumber(point.score) }} 分</div>
            </div>
          </div>
        </div>

        <div v-if="improvementReference.available" class="card result-page__improvement-card" style="margin-top: 12px">
          <div class="result-page__improvement-head">
            <div>
              <h4 class="result-page__improvement-title">进步参考</h4>
              <p class="result-page__improvement-basis">{{ improvementReference.basis }}</p>
            </div>
            <a-tag color="blue">依据题库与评分结果生成</a-tag>
          </div>

          <p class="result-page__improvement-summary">{{ improvementReference.summary }}</p>

          <div v-if="improvementReference.teacherComment" class="result-page__teacher-note">
            <span class="result-page__teacher-note-label">老师批注</span>
            <p>{{ improvementReference.teacherComment }}</p>
          </div>

          <div v-if="improvementReference.diagnosisItems.length" class="result-page__improvement-block">
            <h5>这道题目前最影响得分的地方</h5>
            <div class="result-page__diagnosis-list">
              <div
                v-for="item in improvementReference.diagnosisItems"
                :key="item"
                class="result-page__diagnosis-item"
              >
                {{ item }}
              </div>
            </div>
          </div>

          <div v-if="improvementReference.focusPoints.length" class="result-page__improvement-block">
            <h5>老师希望你重点展开的得分层次</h5>
            <div class="result-page__focus-list">
              <div
                v-for="point in improvementReference.focusPoints"
                :key="`${point.order}-${point.title}`"
                class="result-page__focus-item"
              >
                <strong>{{ point.order }}</strong>
                <span>{{ point.title }}</span>
                <p>{{ point.hint }}</p>
              </div>
            </div>
          </div>

          <div v-if="improvementReference.rewriteOpening" class="result-page__improvement-block">
            <h5>开头可以这样改</h5>
            <div class="result-page__rewrite-line">{{ improvementReference.rewriteOpening }}</div>
          </div>

          <div v-if="improvementReference.missingKeywords.length" class="result-page__improvement-block">
            <h5>建议补充关键词</h5>
            <div class="result-page__keyword-list">
              <a-tag
                v-for="keyword in improvementReference.missingKeywords"
                :key="keyword"
                color="orange"
              >
                {{ keyword }}
              </a-tag>
            </div>
          </div>

          <div v-if="improvementReference.weakDimensions.length" class="result-page__improvement-block">
            <h5>当前偏弱维度</h5>
            <div class="result-page__weak-list">
              <div
                v-for="item in improvementReference.weakDimensions"
                :key="`${item.name}-${item.reason}`"
                class="result-page__weak-item"
              >
                <strong>{{ item.name }}</strong>
                <span>{{ item.reason }}</span>
              </div>
            </div>
          </div>

          <div v-if="improvementReference.expressionUpgrades.length" class="result-page__improvement-block">
            <h5>更像高分答案的说法</h5>
            <div class="result-page__upgrade-list">
              <div
                v-for="(item, index) in improvementReference.expressionUpgrades"
                :key="`${index}-${item.before}`"
                class="result-page__upgrade-item"
              >
                <div class="result-page__upgrade-before">
                  <span>偏弱说法</span>
                  <p>{{ item.before }}</p>
                </div>
                <div class="result-page__upgrade-after">
                  <span>建议改成</span>
                  <p>{{ item.after }}</p>
                </div>
              </div>
            </div>
          </div>

          <div v-if="improvementReference.sampleAnswer" class="result-page__improvement-block">
            <h5>老师示范改写</h5>
            <div class="result-page__sample-answer">{{ improvementReference.sampleAnswer }}</div>
          </div>

          <div v-if="improvementReference.rewriteClosing" class="result-page__improvement-block">
            <h5>结尾可以这样收束</h5>
            <div class="result-page__rewrite-line">{{ improvementReference.rewriteClosing }}</div>
          </div>
        </div>

        <div class="card result-page__secondary-card" style="margin-top: 12px">
          <div class="result-page__secondary-head">
            <div>
              <h4 class="result-page__secondary-title">维度表现</h4>
              <p class="result-page__secondary-hint">辅助参考，主分数以上方本题得分为准</p>
            </div>
          </div>
          <RadarChart :dimensions="result.dimensions" size="small" />
        </div>

        <div style="margin-top: 12px">
          <LossAnalysis :dimensions="result.dimensions" compact />
        </div>

        <div style="margin-top: 12px">
          <ScoreBreakdown :keywords="result.matchedKeywords" />
        </div>

        <div style="margin-top: 12px">
          <TranscriptViewer
            :transcript="result.highlightedTranscript || transcript"
            :keywords="result.matchedKeywords"
          />
        </div>
      </div>

      <SpeechAnalysisPanel v-if="speechAnalysis" :analysis="speechAnalysis" />

      <div class="card" style="margin-top: 12px" v-if="currentRecordingUrl" data-html2canvas-ignore>
        <h4 class="section-title">作答录音回放</h4>
        <div class="playback-controls">
          <audio :src="currentRecordingUrl" controls style="width: 100%"></audio>
        </div>
      </div>

      <div class="card result-page__video-card" style="margin-top: 12px" v-if="currentVideoUrl" data-html2canvas-ignore>
        <div class="result-page__video-head">
          <h4 class="section-title">作答视频回放</h4>
          <a-button size="small" @click="openFloatingVideo">
            <VideoCameraOutlined /> 画中画
          </a-button>
        </div>
        <video
          :src="currentVideoUrl"
          controls
          class="result-page__video"
          @play="openFloatingVideo"
        ></video>
      </div>

      <div
        v-if="floatingVideoVisible && currentVideoUrl"
        class="result-page__floating-video"
        data-html2canvas-ignore
        @click="closeFloatingVideo"
      >
        <video
          :key="currentVideoUrl"
          :src="currentVideoUrl"
          controls
          autoplay
          muted
          playsinline
          class="result-page__floating-video-player"
          @click.stop
        ></video>
        <button class="result-page__floating-video-close" type="button" @click.stop="closeFloatingVideo">
          <CloseOutlined />
        </button>
      </div>

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
import {
  CloseOutlined,
  FilePdfOutlined,
  StarOutlined,
  StarFilled,
  ShareAltOutlined,
  VideoCameraOutlined
} from '@ant-design/icons-vue'
import { useExamStore } from '@/stores/exam'
import { useFavoritesStore } from '@/stores/favorites'
import { useTrainingStore } from '@/stores/training'
import { getGrade } from '@/utils/constants'
import { getHistoryDetail } from '@/api/history'
import { getQuestionById } from '@/api/questionBank'
import { usePdfExport } from '@/composables/usePdfExport'
import { analyzeSpeech } from '@/composables/useSpeechAnalysis'
import { buildImprovementReference } from '@/utils/questionPresentation'
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

const answerList = ref([])
const currentAnswerIdx = ref(0)
const blobUrls = ref([])
const questionDetailsMap = ref({})
const floatingVideoVisible = ref(false)

const activeExamId = computed(() => String(examStore.examId || route.params.examId || ''))
const currentAnswer = computed(() => answerList.value[currentAnswerIdx.value] || null)
const currentQuestion = computed(() => {
  const answer = currentAnswer.value
  if (!answer?.questionId) return null
  return examStore.questionList?.find((item) => item.id === answer.questionId)
    || questionDetailsMap.value[answer.questionId]
    || null
})
const currentQuestionLabel = computed(() => (
  `${answerList.value.length > 1 ? `第 ${currentAnswerIdx.value + 1} 题` : '本题'}${currentAnswer.value?.isPlaceholder ? ' · 未作答' : ''}`
))
const currentQuestionStem = computed(() => currentQuestion.value?.stem || currentAnswer.value?.questionStem || '')
const currentScoringPoints = computed(() => {
  const points = currentQuestion.value?.scoringPoints
  if (!Array.isArray(points)) return []

  return points
    .map((item) => ({
      content: String(item?.content || item?.name || '').trim(),
      score: toFiniteNumber(item?.score, 0)
    }))
    .filter((item) => item.content)
})
const completedAnswerCount = computed(() => answerList.value.filter((answer) => !answer?.isPlaceholder && answer?.scoringResult).length)
const placeholderAnswerCount = computed(() => answerList.value.filter((answer) => answer?.isPlaceholder || !answer?.scoringResult).length)
const currentQuestionAssignedScore = computed(() => currentScoringPoints.value.reduce((sum, item) => sum + item.score, 0))
const improvementReference = computed(() => {
  const rawTranscript = currentAnswer.value?.transcript || transcript.value || ''
  if (currentAnswer.value?.isPlaceholder || isNoContentTranscript(rawTranscript, result.value)) return buildNoContentImprovementReference()

  const modelReference = normalizeModelImprovementSuggestion(result.value?.answerImprovementSuggestion)
  if (modelReference) return modelReference

  return buildImprovementReference({
    question: currentQuestion.value || {},
    result: result.value || {},
    transcript: rawTranscript
  })
})

function getDefaultDimensions() {
  return [
    { name: '综合分析', key: 'analysis', score: 0, maxScore: 20, lostReasons: [] },
    { name: '实务落地', key: 'practical', score: 0, maxScore: 20, lostReasons: [] },
    { name: '应急应变', key: 'emergency', score: 0, maxScore: 15, lostReasons: [] },
    { name: '行政思维', key: 'legal', score: 0, maxScore: 15, lostReasons: [] },
    { name: '逻辑结构', key: 'logic', score: 0, maxScore: 15, lostReasons: [] },
    { name: '语言表达', key: 'expression', score: 0, maxScore: 15, lostReasons: [] }
  ]
}

function getQuestionAssignedScore(question) {
  const points = Array.isArray(question?.scoringPoints) ? question.scoringPoints : []
  return points.reduce((sum, item) => sum + toFiniteNumber(item?.score, 0), 0)
}

function normalizeScoringResult(value = {}, question = null) {
  const totalScore = Number(value?.totalScore ?? value?.score ?? 0) || 0
  const questionMaxScore = getQuestionAssignedScore(question)
  const maxScore = Number(value?.maxScore ?? questionMaxScore ?? 100) || 100
  const questionScore = value?.questionScore !== undefined && value?.questionScore !== null
    ? toFiniteNumber(value.questionScore, totalScore)
    : totalScore
  const questionMax = Number(value?.questionMaxScore ?? questionMaxScore ?? maxScore) || maxScore
  return {
    ...value,
    totalScore,
    maxScore,
    questionScore,
    questionMaxScore: questionMax,
    dimensions: Array.isArray(value?.dimensions) && value.dimensions.length ? value.dimensions : getDefaultDimensions(),
    aiComment: String(
      value?.aiComment
      || value?.comment
      || (String(value?.scoringMode || '').trim() === 'empty_zero' ? '本题未作答，按空答案记 0 分。' : '暂无评语')
    ).trim(),
    scoringMode: String(value?.scoringMode || '').trim()
  }
}

function buildEmptyScoringResult(question = null) {
  const questionMaxScore = getQuestionAssignedScore(question) || 100
  return normalizeScoringResult({
    totalScore: 0,
    maxScore: questionMaxScore,
    questionScore: 0,
    questionMaxScore,
    grade: 'D',
    dimensions: getDefaultDimensions(),
    aiComment: '本题未作答，按空答案记 0 分。',
    scoringMode: 'empty_zero'
  }, question)
}

function buildHistorySummaryResult(detail = {}) {
  return normalizeScoringResult({
    totalScore: detail?.totalScore || 0,
    maxScore: detail?.maxScore || 100,
    grade: detail?.grade || '',
    dimensions: detail?.dimensions || [],
    aiComment: detail?.questionSummary || '历史练习记录'
  })
}

function buildDisplayAnswerList(answers = [], questionIds = [], examId = '') {
  const normalizedAnswers = Array.isArray(answers) ? answers.filter(Boolean) : []
  const questionOrder = Array.isArray(questionIds) ? questionIds.map((id) => String(id || '').trim()).filter(Boolean) : []
  const answerMap = new Map()

  normalizedAnswers.forEach((answer, index) => {
    const questionId = String(answer?.questionId || '').trim()
    if (!questionId) return
    answerMap.set(questionId, {
      ...answer,
      questionId,
      questionIndex: Number.isFinite(Number(answer?.questionIndex)) ? Number(answer.questionIndex) : index
    })
  })

  if (questionOrder.length) {
    const displayAnswers = questionOrder.map((questionId, index) => {
      const matched = answerMap.get(questionId)
      if (matched) {
        return {
          ...matched,
          questionIndex: Number.isFinite(Number(matched.questionIndex)) ? Number(matched.questionIndex) : index
        }
      }
      return {
        examId,
        questionId,
        questionIndex: index,
        questionStem: '',
        transcript: '',
        scoringResult: null,
        answerTiming: null,
        submittedAt: '',
        isPlaceholder: true
      }
    })

    const appendedAnswers = normalizedAnswers.filter((answer) => !questionOrder.includes(String(answer?.questionId || '').trim()))
    return [...displayAnswers, ...appendedAnswers]
      .filter((answer) => String(answer?.questionId || '').trim())
      .sort((a, b) => {
        const aIndex = Number.isFinite(Number(a?.questionIndex)) ? Number(a.questionIndex) : 0
        const bIndex = Number.isFinite(Number(b?.questionIndex)) ? Number(b.questionIndex) : 0
        if (aIndex !== bIndex) return aIndex - bIndex
        return String(a.questionId || '').localeCompare(String(b.questionId || ''))
      })
  }

  return normalizedAnswers
    .filter((answer) => String(answer?.questionId || '').trim())
    .map((answer, index) => ({
      ...answer,
      questionId: String(answer.questionId || '').trim(),
      questionIndex: Number.isFinite(Number(answer?.questionIndex)) ? Number(answer.questionIndex) : index
    }))
    .sort((a, b) => {
      const aIndex = Number.isFinite(Number(a?.questionIndex)) ? Number(a.questionIndex) : 0
      const bIndex = Number.isFinite(Number(b?.questionIndex)) ? Number(b.questionIndex) : 0
      if (aIndex !== bIndex) return aIndex - bIndex
      return String(a.questionId || '').localeCompare(String(b.questionId || ''))
    })
}

function buildPreferredQuestionId(answers = [], questionIds = [], fallback = '') {
  const normalizedQuestionIds = Array.isArray(questionIds) ? questionIds.map((id) => String(id || '').trim()).filter(Boolean) : []
  const normalizedAnswers = Array.isArray(answers) ? answers.filter((item) => String(item?.questionId || '').trim()) : []
  if (fallback) return String(fallback).trim()
  if (normalizedAnswers.length) return String(normalizedAnswers[normalizedAnswers.length - 1]?.questionId || '').trim()
  if (normalizedQuestionIds.length) return normalizedQuestionIds[0]
  return ''
}

function toFiniteNumber(value, fallback = 0) {
  const number = Number(value)
  return Number.isFinite(number) ? number : fallback
}

function formatScoreNumber(value) {
  const number = toFiniteNumber(value)
  return Number.isInteger(number) ? String(number) : number.toFixed(2).replace(/\.?0+$/, '')
}

function normalizeTextList(value) {
  return Array.isArray(value) ? value.map((item) => String(item || '').trim()).filter(Boolean) : []
}

function isNoContentTranscript(value, scoring = {}) {
  const text = String(value || '').trim()
  const mode = String(scoring?.scoringMode || '').trim()
  return text === '未作答'
    || ['screened_zero', 'empty_zero'].includes(mode)
    || text.includes('未能识别出有效语音')
    || text.includes('未配置真实语音转写服务')
    || text.includes('无法生成可靠文字稿')
}

function buildNoContentImprovementReference() {
  return {
    available: true,
    basis: '未识别到有效作答，本卡片仅提示下一步操作。',
    summary: '本次没有可分析的作答内容，请先完成一段有效作答后再查看细化建议。',
    teacherComment: '',
    diagnosisItems: ['未形成可用于复盘的有效作答文本'],
    focusPoints: [],
    missingKeywords: [],
    weakDimensions: [],
    expressionUpgrades: [],
    sampleAnswer: '',
    rewriteOpening: '',
    rewriteClosing: ''
  }
}

function normalizeModelImprovementSuggestion(value) {
  if (!value || typeof value !== 'object') return null
  const focusPoints = Array.isArray(value.focusPoints)
    ? value.focusPoints.map((item, index) => ({
        order: String(item?.order || index + 1),
        title: String(item?.title || item?.name || '').trim(),
        hint: String(item?.hint || item?.content || '').trim()
      })).filter((item) => item.title || item.hint)
    : []
  const expressionUpgrades = Array.isArray(value.expressionUpgrades)
    ? value.expressionUpgrades.map((item) => ({
        before: String(item?.before || '').trim(),
        after: String(item?.after || '').trim()
      })).filter((item) => item.before || item.after)
    : []

  return {
    available: true,
    basis: value.source === 'model'
      ? '由评分模型结合题干、采分点、关键词、作答文本和本次评分结果生成。'
      : '模型建议不可用，已使用题库与评分结果生成基础建议。',
    summary: String(value.summary || '').trim(),
    teacherComment: String(value.teacherComment || '').trim(),
    diagnosisItems: normalizeTextList(value.diagnosisItems),
    focusPoints,
    missingKeywords: normalizeTextList(value.missingKeywords),
    weakDimensions: [],
    expressionUpgrades,
    sampleAnswer: String(value.sampleAnswer || '').trim(),
    rewriteOpening: String(value.rewriteOpening || '').trim(),
    rewriteClosing: String(value.rewriteClosing || '').trim()
  }
}

function getAnswerAssignedScore(question) {
  const points = Array.isArray(question?.scoringPoints) ? question.scoringPoints : []
  return points.reduce((sum, item) => sum + toFiniteNumber(item?.score, 0), 0)
}

function getAnswerScorePair(answer, question = null) {
  const scoring = answer?.scoringResult || {}
  const questionMaxScore = toFiniteNumber(scoring.questionMaxScore, 0)
  const assignedScore = getAnswerAssignedScore(question)
  const maxScore = questionMaxScore > 0
    ? questionMaxScore
    : assignedScore > 0
      ? assignedScore
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
  if (answer?.isPlaceholder || !answer?.scoringResult) return '未作答'
  const question = examStore.questionList?.find((item) => item.id === answer?.questionId)
    || questionDetailsMap.value[answer?.questionId]
    || null
  const { score, maxScore } = getAnswerScorePair(answer, question)
  return `${formatScoreNumber(score)}/${formatScoreNumber(maxScore)}分`
}

const currentScorePair = computed(() => getAnswerScorePair(
  currentAnswer.value || { scoringResult: result.value },
  currentQuestion.value
))
const displayQuestionScore = computed(() => formatScoreNumber(currentScorePair.value.score))
const displayQuestionMaxScore = computed(() => formatScoreNumber(currentScorePair.value.maxScore))
const displayTotalScore = computed(() => formatScoreNumber(result.value?.totalScore || 0))
const displayMaxScore = computed(() => formatScoreNumber(result.value?.maxScore || 100))
const answerTabsLabel = computed(() => (
  answerList.value.length > 1 ? `已答 ${completedAnswerCount.value} 题，未答 ${placeholderAnswerCount.value} 题` : ''
))

const gradeInfo = computed(() => {
  if (!result.value) return { label: '', color: '' }
  return getGrade(result.value.totalScore, result.value.maxScore)
})

const scoringModeLabel = computed(() => {
  const mode = String(result.value?.scoringMode || '').trim()
  const labels = {
    llm: '模型评分',
    rule_based: '规则兜底',
    screened_zero: '无效作答筛查',
    conservative: '保守评分',
    ai_gongwu_text: '外部评分引擎'
  }
  return labels[mode] || mode
})

function normalizeMediaUrl(url) {
  const value = String(url || '').trim()
  if (!value) return ''
  const token = localStorage.getItem('token') || ''
  if (token && value.startsWith('/api/exam/') && !value.includes('access_token=')) {
    const separator = value.includes('?') ? '&' : '?'
    return `${value}${separator}access_token=${encodeURIComponent(token)}`
  }
  if (value.startsWith('blob:') || value.startsWith('http://') || value.startsWith('https://') || value.startsWith('/')) {
    return value
  }
  return `/${value}`
}

const currentMediaUrl = computed(() => {
  const blobUrl = blobUrls.value[currentAnswerIdx.value]
  if (blobUrl) return blobUrl
  return normalizeMediaUrl(currentAnswer.value?.mediaUrl)
})

const currentMediaType = computed(() => {
  const answer = currentAnswer.value
  return String(answer?.recordingBlob?.type || answer?.mediaType || '')
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

function ansScoreColor(answer) {
  if (answer?.isPlaceholder || !answer?.scoringResult) return '#8C8C8C'
  const { score, maxScore } = getAnswerScorePair(answer)
  const ratio = score / maxScore
  if (ratio >= 0.85) return '#389E0D'
  if (ratio >= 0.75) return '#1B5FAA'
  if (ratio >= 0.6) return '#D48806'
  return '#CF1322'
}

const speechAnalysis = computed(() => {
  const answer = currentAnswer.value
  const rawTranscript = answer?.transcript || transcript.value || ''
  if (isNoContentTranscript(rawTranscript, answer?.scoringResult || result.value)) return null

  const duration = Number(
    answer?.duration
    || answer?.durationSeconds
    || answer?.recordingDuration
    || answer?.mediaDuration
    || 0
  )
  if (!Number.isFinite(duration) || duration <= 0) return null

  return analyzeSpeech(rawTranscript, duration)
})

function revokeBlobUrls() {
  blobUrls.value.forEach((url) => {
    if (url?.startsWith('blob:')) {
      URL.revokeObjectURL(url)
    }
  })
}

function openFloatingVideo() {
  if (!currentVideoUrl.value) return
  floatingVideoVisible.value = true
}

function closeFloatingVideo() {
  floatingVideoVisible.value = false
}

function syncDisplayedAnswer(answer) {
  if (!answer) return
  const question = examStore.questionList?.find((item) => item.id === answer?.questionId)
    || questionDetailsMap.value[answer?.questionId]
    || null
  result.value = answer.scoringResult || buildEmptyScoringResult(question)
  transcript.value = answer.transcript || ''
}

function syncAnswerList(answers) {
  const normalizedAnswers = (answers || [])
    .filter((answer) => answer?.questionId || answer?.scoringResult)
    .map((answer, index) => ({
      ...answer,
      questionIndex: Number.isFinite(Number(answer?.questionIndex)) ? Number(answer.questionIndex) : index
    }))
  revokeBlobUrls()
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
  return true
}

async function hydrateQuestionDetails(answers = []) {
  const ids = Array.from(
    new Set(
      answers
        .map((answer) => answer?.questionId)
        .filter(Boolean)
    )
  ).filter((id) => !questionDetailsMap.value[id])

  if (!ids.length) return

  const fetched = await Promise.all(ids.map(async (id) => {
    try {
      return await getQuestionById(id)
    } catch {
      return null
    }
  }))

  const nextMap = { ...questionDetailsMap.value }
  fetched.forEach((question) => {
    if (question?.id) {
      nextMap[question.id] = question
    }
  })
  questionDetailsMap.value = nextMap
}

function syncLoadedAnswers(detail = {}, answers = []) {
  const questionIds = Array.isArray(detail?.questionIds) ? detail.questionIds : []
  const examId = String(detail?.examId || activeExamId.value || '')
  const displayAnswers = buildDisplayAnswerList(answers, questionIds, examId).map((answer) => {
    const question = examStore.questionList?.find((item) => item.id === answer.questionId)
      || questionDetailsMap.value[answer.questionId]
      || null
    const scoringResult = answer.scoringResult ? normalizeScoringResult(answer.scoringResult, question) : buildEmptyScoringResult(question)
    return {
      ...answer,
      questionStem: answer.questionStem || question?.stem || '',
      province: answer.province || question?.province || detail?.province || 'national',
      scoringResult,
      transcript: answer.transcript || (answer.scoringResult ? '' : '未作答'),
      answerTiming: answer.answerTiming || scoringResult.answerTiming || null
    }
  })

  answerList.value = displayAnswers
  currentAnswerIdx.value = 0
  return displayAnswers
}

function enrichAnswerListWithQuestions() {
  answerList.value = answerList.value.map((answer) => {
    const question = examStore.questionList?.find((item) => item.id === answer?.questionId)
      || questionDetailsMap.value[answer?.questionId]
      || null
    if (!question) return answer
    const scoringResult = answer.scoringResult
      ? normalizeScoringResult(answer.scoringResult, question)
      : buildEmptyScoringResult(question)
    return {
      ...answer,
      questionStem: answer.questionStem || question.stem || '',
      province: answer.province || question.province || 'national',
      scoringResult
    }
  })
}

function syncFallbackFromDetail(detail = {}) {
  result.value = buildHistorySummaryResult(detail)
  transcript.value = ''
  answerList.value = []
  currentAnswerIdx.value = 0
  return result.value
}

watch(currentAnswerIdx, (idx) => {
  closeFloatingVideo()
  syncDisplayedAnswer(answerList.value[idx])
})

const isStarred = computed(() => {
  const answer = currentAnswer.value
  if (!answer || answer.isPlaceholder || !activeExamId.value) return false
  return favoritesStore.isFavorited(activeExamId.value, answer.questionId)
})

function toggleFavorite() {
  const answer = currentAnswer.value
  if (!answer || answer.isPlaceholder || !answer.questionId || !result.value || !activeExamId.value) return

  const question = examStore.questionList?.find((item) => item.id === answer.questionId)
  if (isStarred.value) {
    const item = favoritesStore.items.find((entry) => (
      entry.examId === activeExamId.value && entry.questionId === answer.questionId
    ))
    if (item) favoritesStore.removeItem(item.id, 'starred')
    return
  }

  favoritesStore.addItem({
    examId: activeExamId.value,
    questionId: answer.questionId,
    questionStem: question?.stem || answer.questionStem || '',
    dimension: question?.dimension || answer.dimension || '',
    score: result.value.totalScore,
    maxScore: result.value.maxScore,
    grade: gradeInfo.value.label,
    type: 'starred'
  })
}

function autoAddWeakAll() {
  if (!activeExamId.value) return

  for (const answer of answerList.value) {
    if (answer?.isPlaceholder || !answer?.scoringResult || !answer?.questionId) continue
    const ratio = answer.scoringResult.totalScore / answer.scoringResult.maxScore
    if (ratio >= 0.6) continue

    const question = examStore.questionList?.find((item) => item.id === answer.questionId)
    favoritesStore.addItem({
      examId: activeExamId.value,
      questionId: answer.questionId,
      questionStem: question?.stem || answer.questionStem || '',
      dimension: question?.dimension || answer.dimension || '',
      score: answer.scoringResult.totalScore,
      maxScore: answer.scoringResult.maxScore,
      grade: getGrade(answer.scoringResult.totalScore, answer.scoringResult.maxScore).label,
      type: 'weak'
    })
  }
}

function recordTrainingProgress() {
  const recordKey = `training-progress-recorded:${activeExamId.value || 'local'}`
  if (sessionStorage.getItem(recordKey)) return

  let hasRecorded = false

  for (const answer of answerList.value) {
    if (answer?.isPlaceholder || !answer?.scoringResult || !answer?.questionId) continue

    const question = examStore.questionList?.find((item) => item.id === answer.questionId)
    const trainingCategoryKey = question?.trainingCategoryKey
    if (!trainingCategoryKey) continue

    trainingStore.recordTrainingResult(trainingCategoryKey, Number(answer.scoringResult.totalScore) || 0)
    hasRecorded = true
  }

  if (hasRecorded) {
    sessionStorage.setItem(recordKey, '1')
  }
}

function handleExportPdf() {
  if (!pdfContentRef.value) return
  const examId = route.params.examId || 'report'
  exportToPdf(pdfContentRef.value, `测评报告_${examId}`)
}

function openShareCard() {
  shareCardRef.value?.open()
}

onMounted(async () => {
  if (examStore.answers.length > 0) {
    syncAnswerList(examStore.answers)
    await hydrateQuestionDetails(examStore.answers)
    enrichAnswerListWithQuestions()
    syncDisplayedAnswer(answerList.value[currentAnswerIdx.value])
    loading.value = false
    autoAddWeakAll()
    recordTrainingProgress()
    return
  }

  if (examStore.scoringResult) {
    syncAnswerList([{
      questionId: examStore.currentQuestion?.id,
      recordingBlob: examStore.recordingBlob,
      transcript: examStore.transcript,
      scoringResult: examStore.scoringResult
    }])
    await hydrateQuestionDetails(answerList.value)
    enrichAnswerListWithQuestions()
    syncDisplayedAnswer(answerList.value[currentAnswerIdx.value])
    loading.value = false
    autoAddWeakAll()
    recordTrainingProgress()
    return
  }

  const examId = String(route.params.examId || '')

  try {
    const detail = await getHistoryDetail(examId)
    const answers = Array.isArray(detail?.answers) ? detail.answers : []
    const questionIds = Array.isArray(detail?.questionIds) ? detail.questionIds : []
    const orderedAnswers = buildDisplayAnswerList(answers, questionIds, examId)
    await hydrateQuestionDetails(orderedAnswers)
    const displayAnswers = syncLoadedAnswers(detail, orderedAnswers)
    if (displayAnswers.length) {
      const preferredQuestionId = buildPreferredQuestionId(answers, questionIds)
      const preferredIndex = Math.max(0, displayAnswers.findIndex((answer) => answer.questionId === preferredQuestionId))
      currentAnswerIdx.value = preferredIndex
      syncDisplayedAnswer(displayAnswers[preferredIndex])
    } else {
      syncFallbackFromDetail(detail)
    }
  } catch {
    // History detail is the source of truth for whole-exam results.
  } finally {
    loading.value = false
    autoAddWeakAll()
    recordTrainingProgress()
  }
})

onUnmounted(() => {
  closeFloatingVideo()
  revokeBlobUrls()
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

.result-page__assignment-card {
  padding: 16px;
}

.result-page__assignment-head {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 12px;
}

.result-page__assignment-title {
  margin: 0;
  font-size: @font-size-lg;
  color: @text-primary;
}

.result-page__assignment-hint {
  margin: 6px 0 0;
  color: @text-secondary;
  font-size: @font-size-xs;
}

.result-page__assignment-list {
  display: grid;
  gap: 10px;
  margin-top: 14px;
}

.result-page__assignment-item {
  display: grid;
  grid-template-columns: 84px minmax(0, 1fr) auto;
  gap: 12px;
  align-items: start;
  padding: 12px 14px;
  border-radius: 14px;
  background: #fafcff;
  border: 1px solid rgba(27, 95, 170, 0.08);
}

.result-page__assignment-index {
  color: @text-secondary;
  font-size: @font-size-xs;
  line-height: 1.8;
}

.result-page__assignment-content {
  color: @text-regular;
  font-size: @font-size-sm;
  line-height: 1.8;
}

.result-page__assignment-score {
  color: #1B5FAA;
  font-size: @font-size-sm;
  font-weight: 700;
  white-space: nowrap;
}

.result-page__improvement-card {
  padding: 18px 16px;
}

.result-page__improvement-head {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  gap: 12px;
}

.result-page__improvement-title {
  margin: 0;
  font-size: @font-size-lg;
  color: @text-primary;
}

.result-page__improvement-basis {
  margin: 6px 0 0;
  font-size: @font-size-xs;
  color: @text-secondary;
}

.result-page__improvement-summary {
  margin: 14px 0 0;
  color: @text-regular;
  font-size: @font-size-sm;
  line-height: 1.8;
}

.result-page__teacher-note {
  margin-top: 16px;
  padding: 14px;
  border-radius: 14px;
  background: linear-gradient(180deg, rgba(27, 95, 170, 0.06) 0%, rgba(95, 160, 232, 0.05) 100%);
  border: 1px solid rgba(27, 95, 170, 0.08);
}

.result-page__teacher-note-label {
  display: inline-flex;
  align-items: center;
  min-height: 24px;
  padding: 0 8px;
  border-radius: 999px;
  background: rgba(27, 95, 170, 0.1);
  color: #1b5faa;
  font-size: 12px;
  font-weight: 600;
}

.result-page__teacher-note p {
  margin: 10px 0 0;
  color: @text-regular;
  font-size: @font-size-sm;
  line-height: 1.9;
}

.result-page__improvement-block {
  margin-top: 16px;
}

.result-page__improvement-block h5 {
  margin: 0 0 10px;
  color: @text-primary;
  font-size: @font-size-base;
}

.result-page__focus-list,
.result-page__weak-list,
.result-page__diagnosis-list,
.result-page__upgrade-list {
  display: grid;
  gap: 10px;
}

.result-page__focus-item,
.result-page__weak-item,
.result-page__diagnosis-item,
.result-page__upgrade-item {
  padding: 12px 14px;
  border-radius: 14px;
  background: #fafcff;
  border: 1px solid rgba(27, 95, 170, 0.08);
}

.result-page__diagnosis-item {
  color: @text-regular;
  font-size: @font-size-sm;
  line-height: 1.85;
}

.result-page__focus-item strong,
.result-page__weak-item strong {
  display: block;
  color: @text-primary;
  font-size: @font-size-sm;
}

.result-page__focus-item span,
.result-page__weak-item span {
  display: block;
  margin-top: 4px;
  color: @text-regular;
  line-height: 1.7;
}

.result-page__focus-item p {
  margin: 6px 0 0;
  color: @text-secondary;
  font-size: @font-size-xs;
  line-height: 1.7;
}

.result-page__keyword-list {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.result-page__upgrade-item {
  display: grid;
  gap: 12px;
}

.result-page__upgrade-before,
.result-page__upgrade-after {
  display: grid;
  gap: 6px;
}

.result-page__upgrade-before span,
.result-page__upgrade-after span {
  color: @text-secondary;
  font-size: @font-size-xs;
}

.result-page__upgrade-before p,
.result-page__upgrade-after p {
  margin: 0;
  color: @text-regular;
  font-size: @font-size-sm;
  line-height: 1.85;
}

.result-page__upgrade-after {
  padding: 12px;
  border-radius: 12px;
  background: rgba(56, 158, 13, 0.05);
  border: 1px solid rgba(56, 158, 13, 0.1);
}

.result-page__rewrite-line {
  padding: 14px;
  border-radius: 14px;
  background: #fffdf7;
  border: 1px solid rgba(212, 135, 25, 0.14);
  color: @text-regular;
  font-size: @font-size-sm;
  line-height: 1.9;
}

.result-page__sample-answer {
  padding: 14px;
  border-radius: 14px;
  background: linear-gradient(180deg, rgba(27, 95, 170, 0.05) 0%, rgba(95, 160, 232, 0.05) 100%);
  color: @text-regular;
  font-size: @font-size-sm;
  line-height: 1.9;
  white-space: pre-wrap;
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
  margin-top: 12px;
  margin-bottom: 12px;
  overflow-x: auto;
  white-space: nowrap;
}

.answer-tabs__summary {
  margin-bottom: 10px;
  color: @text-secondary;
  font-size: @font-size-sm;
}

.playback-controls {
  padding: 8px 0;
}

.result-page__video-card {
  padding: 16px;
}

.result-page__video-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
}

.result-page__video-head .section-title {
  margin-bottom: 0;
}

.result-page__video {
  display: block;
  width: 100%;
  margin-top: 12px;
  border-radius: 8px;
}

.result-page__floating-video {
  position: fixed;
  right: 24px;
  bottom: 24px;
  z-index: 1200;
  width: min(360px, calc(100vw - 32px));
  aspect-ratio: 16 / 9;
  border-radius: 10px;
  overflow: hidden;
  background: #050505;
  border: 1px solid rgba(255, 255, 255, 0.16);
  box-shadow: 0 18px 46px rgba(16, 24, 40, 0.32);
}

.result-page__floating-video-player {
  display: block;
  width: 100%;
  height: 100%;
  object-fit: contain;
}

.result-page__floating-video-close {
  position: absolute;
  top: 8px;
  right: 8px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 28px;
  height: 28px;
  padding: 0;
  border: 0;
  border-radius: 50%;
  background: rgba(0, 0, 0, 0.58);
  color: #fff;
  cursor: pointer;
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

  .result-page__assignment-item {
    grid-template-columns: 1fr;
  }
}
</style>
