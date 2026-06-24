<!--
小程序结果页，展示评分后的总分、能力维度、文字稿、扣分分析、建议和历史保存状态。

这里是评分后页面，可以展示分数和诊断；考场页不能提前暴露这些内容。能力维度与训练题型分类保持分离，
数据不足时宁可隐藏图表，也不要用题型分类硬凑能力雷达。

@param: 无；结果来自 exam store、路由参数或历史结果接口。
@return: 渲染评分结果、复盘内容、重练/分享入口和异常空态。
@raises: 不主动抛业务异常；结果缺失、接口失败或分享失败由页面提示承接。
-->
<template>
  <view class="page">
    <template v-if="result">
      <view class="result-hero card">
        <view class="result-hero__copy">
          <text class="result-hero__kicker">模型评测结果 · {{ currentQuestionLabel }}</text>
          <text class="result-hero__score">{{ result.totalScore }}/{{ result.maxScore }} 分</text>
          <text class="result-hero__grade" :style="{ color: grade.color }">{{ grade.label }}</text>
        </view>
        <ScoreRing :score="result.totalScore" :max-score="result.maxScore" size="medium" :color="grade.color" />
      </view>

      <view v-if="answerList.length > 1" class="card answer-tabs">
        <text class="answer-tabs__summary">已答 {{ completedAnswerCount }} 题，未答 {{ unansweredCount }} 题</text>
        <scroll-view scroll-x class="answer-tabs__scroll">
          <view class="answer-tabs__row">
            <button
              v-for="(item, index) in answerList"
              :key="`${item.questionId || index}-${index}`"
              class="answer-tab"
              :class="{ 'answer-tab--active': index === activeAnswerIndex, 'answer-tab--empty': item.isPlaceholder }"
              @tap="selectAnswer(index)"
            >
              第 {{ index + 1 }} 题 {{ formatAnswerScore(item) }}
            </button>
          </view>
        </scroll-view>
      </view>

      <view class="card local-fit-card">
        <view class="section-head">
          <text class="section-title">本土岗位贴合度</text>
        </view>
        <view class="local-fit-card__tags">
          <text class="local-fit-card__tag">{{ localFitProvinceName }}</text>
          <text class="local-fit-card__tag">岗位场景识别</text>
        </view>
        <text class="local-fit-card__desc">
          本次复盘会重点关注作答是否回应本地治理场景、岗位职责和群众服务细节，帮助你把通用答法落到具体岗位语境里。
        </text>
      </view>

      <view v-if="questionStem" class="card">
        <view class="section-head">
          <text class="section-title">题目</text>
        </view>
        <text class="plain-text">{{ questionStem }}</text>
      </view>

      <view v-if="answerTimingView" class="card timing-card">
        <view class="section-head">
          <text class="section-title">答题用时</text>
        </view>
        <text class="timing-card__main">实际用时 {{ formatDuration(answerTimingView.actualSeconds) }}</text>
        <text v-if="answerTimingView.overtimeSeconds > 0" class="timing-card__overtime">
          超时 {{ formatDuration(answerTimingView.overtimeSeconds) }}
        </text>
      </view>

      <view class="card">
        <view class="section-head">
          <text class="section-title">AI 评语</text>
        </view>
        <text class="ai-generated-note">由AI生成，仅供参考</text>
        <text class="plain-text">{{ result.aiComment }}</text>
      </view>

      <view v-if="improvementSuggestion" class="card improvement-card">
        <view class="section-head">
          <text class="section-title">进步参考</text>
          <text class="improvement-card__source">{{ suggestionSourceLabel }}</text>
        </view>
        <text class="ai-generated-note">由AI生成，仅供参考</text>
        <text class="improvement-card__summary">{{ improvementSuggestion.summary }}</text>

        <view v-if="improvementSuggestion.teacherComment" class="teacher-note">
          <text class="teacher-note__label">老师批注</text>
          <text class="teacher-note__text">{{ improvementSuggestion.teacherComment }}</text>
        </view>

        <view v-if="improvementSuggestion.diagnosisItems.length" class="suggestion-block">
          <text class="suggestion-block__title">主要影响得分的地方</text>
          <text
            v-for="(item, index) in improvementSuggestion.diagnosisItems"
            :key="`${index}-${item}`"
            class="suggestion-line"
          >
            {{ item }}
          </text>
        </view>

        <view v-if="improvementSuggestion.focusPoints.length" class="suggestion-block">
          <text class="suggestion-block__title">下一步重点展开</text>
          <view
            v-for="point in improvementSuggestion.focusPoints"
            :key="`${point.order}-${point.title}`"
            class="focus-item"
          >
            <text class="focus-item__order">{{ point.order }}</text>
            <view class="focus-item__copy">
              <text class="focus-item__title">{{ point.title }}</text>
              <text class="focus-item__hint">{{ point.hint }}</text>
            </view>
          </view>
        </view>

        <view v-if="improvementSuggestion.rewriteOpening" class="suggestion-block">
          <text class="suggestion-block__title">开头可以这样改</text>
          <text class="rewrite-line">{{ improvementSuggestion.rewriteOpening }}</text>
        </view>

        <view v-if="improvementSuggestion.missingKeywords.length" class="suggestion-block">
          <text class="suggestion-block__title">建议补充关键词</text>
          <view class="keyword-row">
            <text
              v-for="keyword in improvementSuggestion.missingKeywords"
              :key="keyword"
              class="keyword-chip"
            >
              {{ keyword }}
            </text>
          </view>
        </view>

        <view v-if="improvementSuggestion.expressionUpgrades.length" class="suggestion-block">
          <text class="suggestion-block__title">更像高分答案的说法</text>
          <view
            v-for="(item, index) in improvementSuggestion.expressionUpgrades"
            :key="`${index}-${item.after}`"
            class="upgrade-item"
          >
            <text class="upgrade-item__before">{{ item.before }}</text>
            <text class="upgrade-item__after">{{ item.after }}</text>
          </view>
        </view>

        <view v-if="improvementSuggestion.sampleAnswer" class="suggestion-block">
          <text class="suggestion-block__title">老师示范改写</text>
          <text class="sample-answer">{{ improvementSuggestion.sampleAnswer }}</text>
        </view>

        <view v-if="improvementSuggestion.rewriteClosing" class="suggestion-block">
          <text class="suggestion-block__title">结尾可以这样收束</text>
          <text class="rewrite-line">{{ improvementSuggestion.rewriteClosing }}</text>
        </view>
      </view>

      <view class="card">
        <view class="section-head">
          <text class="section-title">维度表现</text>
        </view>
        <DimensionBars :dimensions="result.dimensions" />
      </view>

      <view v-if="displayTranscript" class="card">
        <view class="section-head">
          <text class="section-title">作答文本</text>
        </view>
        <text class="plain-text">{{ displayTranscript }}</text>
      </view>
      <view v-else-if="noContentReason" class="card transcript-status-card">
        <view class="section-head">
          <text class="section-title">作答文本</text>
        </view>
        <text class="transcript-status-card__title">{{ noContentReason.title }}</text>
        <text class="transcript-status-card__desc">{{ noContentReason.desc }}</text>
      </view>

      <view class="utility-actions card">
        <button class="secondary-button" @tap="toggleStarred">
          {{ isStarred ? '已收藏' : '收藏本题' }}
        </button>
        <button class="secondary-button" @tap="openShareCard">分享成绩卡</button>
      </view>

      <view class="result-actions">
        <button class="primary-button" @tap="again">再练一题</button>
        <button class="secondary-button" @tap="home">返回首页</button>
      </view>

      <view v-if="shareVisible" class="share-mask" @tap="closeShareCard">
        <view class="share-panel" @tap.stop>
          <view class="share-card">
            <view class="share-card__header">
              <text>公考面试AI智能测评</text>
              <text>{{ shareDate }}</text>
            </view>
            <view class="share-card__score">{{ result.totalScore }}</view>
            <text class="share-card__label">综合得分 / {{ result.maxScore }} 分</text>
            <text class="share-card__grade" :style="{ color: grade.color }">{{ grade.label }}</text>
            <view class="share-card__dims">
              <view v-for="dim in shareDimensions" :key="dim.name" class="share-card__dim">
                <text>{{ dim.name }}</text>
                <text>{{ dim.score }}/{{ dim.maxScore }}</text>
              </view>
            </view>
            <text class="share-card__slogan">每日一练，持续复盘</text>
          </view>
          <button class="primary-button" open-type="share">转发给微信好友</button>
          <button class="secondary-button share-panel__close" @tap="closeShareCard">关闭</button>
        </view>
      </view>
    </template>
    <view v-else class="card">
      <EmptyState title="暂无评分结果" desc="如果刚提交作答，请稍后刷新历史记录。" />
    </view>
  </view>
</template>

<script setup>
import { computed, ref } from 'vue'
import { onLoad, onShareAppMessage } from '@dcloudio/uni-app'
import DimensionBars from '../../components/DimensionBars.vue'
import EmptyState from '../../components/EmptyState.vue'
import ScoreRing from '../../components/ScoreRing.vue'
import { getHistoryDetail } from '../../api/history'
import { getScoringResult } from '../../api/scoring'
import { getQuestionById } from '../../api/questionBank'
import { useExamStore } from '../../stores/exam'
import { useFavoritesStore } from '../../stores/favorites'
import { useTrainingStore } from '../../stores/training'
import { getGrade, getProvinceName } from '../../utils/constants'
import { hideLoading, requireLogin, showLoading, toast } from '../../utils/navigation'
import { normalizeImprovementSuggestion, normalizeResult } from '../../utils/scoring'

const examStore = useExamStore()
const favoritesStore = useFavoritesStore()
const trainingStore = useTrainingStore()
const result = ref(null)
const transcript = ref('')
const questionStem = ref('')
const questionProvince = ref('national')
const answerTiming = ref(null)
const answerList = ref([])
const activeAnswerIndex = ref(0)
const progressRecorded = ref(false)
const weakRecordedQuestionIds = ref(new Set())
const activeExamId = ref('')
const activeQuestionId = ref('')
const shareVisible = ref(false)

const grade = computed(() => getGrade(result.value?.totalScore || 0, result.value?.maxScore || 100))
const localFitProvinceName = computed(() => getProvinceName(questionProvince.value || 'national'))
const currentAnswer = computed(() => answerList.value[activeAnswerIndex.value] || null)
const currentQuestionLabel = computed(() => (
  answerList.value.length > 1
    ? `第 ${activeAnswerIndex.value + 1} 题${currentAnswer.value?.isPlaceholder ? ' · 未作答' : ''}`
    : currentAnswer.value?.isPlaceholder ? '本题 · 未作答' : '本题'
))
const completedAnswerCount = computed(() => answerList.value.filter((answer) => !answer?.isPlaceholder && answer?.scoringResult).length)
const unansweredCount = computed(() => answerList.value.filter((answer) => answer?.isPlaceholder || !answer?.scoringResult).length)
const improvementSuggestion = computed(() => {
  if (currentAnswer.value?.isPlaceholder || isNoContentTranscript(transcript.value, result.value)) return buildNoContentImprovementSuggestion()
  return normalizeImprovementSuggestion(
    result.value?.answerImprovementSuggestion,
    result.value?.totalScore || 0,
    result.value?.maxScore || 100
  )
})
const suggestionSourceLabel = computed(() => (
  improvementSuggestion.value?.source === 'model' ? '模型建议' : '基础建议'
))
const displayTranscript = computed(() => (
  isNoContentTranscript(transcript.value, result.value) ? '' : String(transcript.value || '').trim()
))
const noContentReason = computed(() => resolveNoContentReason(transcript.value, result.value))
const answerTimingView = computed(() => normalizeAnswerTiming(
  answerTiming.value
  || result.value?.answerTiming
  || result.value?.mediaRecord?.answerTiming
  || null
))
const isStarred = computed(() => favoritesStore.isFavorited(activeExamId.value, activeQuestionId.value))
const shareDate = computed(() => new Date().toLocaleDateString('zh-CN'))
const shareDimensions = computed(() => (
  Array.isArray(result.value?.dimensions) ? result.value.dimensions.slice(0, 4) : []
))
const sharePath = computed(() => {
  const params = []
  if (activeExamId.value) params.push(`examId=${encodeURIComponent(activeExamId.value)}`)
  if (activeQuestionId.value) params.push(`questionId=${encodeURIComponent(activeQuestionId.value)}`)
  return `/pages/result/index${params.length ? `?${params.join('&')}` : ''}`
})

onShareAppMessage(() => ({
  title: `我的面试测评得分 ${result.value?.totalScore || 0}/${result.value?.maxScore || 100}`,
  path: sharePath.value
}))

function isNoContentTranscript(value, scoring = {}) {
  const text = String(value || '').trim()
  const mode = String(scoring?.scoringMode || '').trim()
  return text === '未作答'
    || ['screened_zero', 'empty_zero'].includes(mode)
    || text.includes('未能识别出有效语音')
    || text.includes('未配置真实语音转写服务')
    || text.includes('无法生成可靠文字稿')
}

function normalizeAnswerTiming(raw) {
  if (!raw || typeof raw !== 'object') return null
  const actualSeconds = Math.max(0, Number(raw.actualSeconds || raw.usageSeconds || 0) || 0)
  const standardSeconds = Math.max(0, Number(raw.standardSeconds || 0) || 0)
  const overtimeSeconds = Math.max(0, Number(raw.overtimeSeconds || (standardSeconds ? actualSeconds - standardSeconds : 0)) || 0)
  if (!actualSeconds && !standardSeconds) return null
  return { actualSeconds, standardSeconds, overtimeSeconds }
}

function formatDuration(seconds = 0) {
  const total = Math.max(0, Math.round(Number(seconds) || 0))
  const minutes = Math.floor(total / 60)
  const rest = total % 60
  if (minutes <= 0) return `${rest} 秒`
  if (rest <= 0) return `${minutes} 分钟`
  return `${minutes} 分 ${rest} 秒`
}

function resolveNoContentReason(value, scoring = {}) {
  if (!isNoContentTranscript(value, scoring)) return null
  const skipReason = String(scoring?.skipReason || scoring?.asrFailureType || scoring?.mediaRecord?.asrMeta?.status || '').trim()
  const reasonMap = {
    user_confirmed_skip: {
      title: '用户确认跳过',
      desc: '本题未提交录音或录像，已按未作答记 0 分。'
    },
    too_short: {
      title: '录音过短',
      desc: '本次录音时长不足，无法形成可靠文字稿，已按无效作答处理。'
    },
    silent_audio: {
      title: '音量过低或接近静音',
      desc: '本次录音没有足够清晰的人声，建议重新练习时靠近麦克风并保持环境安静。'
    },
    empty_audio: {
      title: '未识别到有效语音',
      desc: '本次录音未识别出可用于评分的作答内容。'
    },
    no_speech: {
      title: '未识别到有效语音',
      desc: '本次录音未识别出可用于评分的作答内容。'
    },
    funasr_error: {
      title: '语音服务异常',
      desc: '本次转写服务异常，建议重新录制后提交。'
    },
    asr_unavailable: {
      title: '语音服务异常',
      desc: '本次转写服务暂不可用，建议稍后重新录制后提交。'
    }
  }
  return reasonMap[skipReason] || {
    title: '无有效作答内容',
    desc: '本次没有可用于复盘的可靠文字稿，请完成一段清晰作答后再查看细化建议。'
  }
}

function buildNoContentImprovementSuggestion() {
  const reason = noContentReason.value
  return {
    source: 'fallback',
    summary: reason?.desc || '本次没有可分析的有效作答内容，请先完成一段录音或录像作答后再查看细化建议。',
    teacherComment: '',
    diagnosisItems: ['未形成可用于复盘的有效作答文本'],
    focusPoints: [],
    missingKeywords: [],
    expressionUpgrades: [],
    sampleAnswer: '',
    rewriteOpening: '',
    rewriteClosing: ''
  }
}

function getQuestionAssignedScore(question = {}) {
  const points = Array.isArray(question?.scoringPoints) ? question.scoringPoints : []
  return points.reduce((sum, item) => sum + (Number(item?.score || 0) || 0), 0)
}

function normalizeDisplayResult(value = {}, question = {}) {
  const normalized = normalizeResult(value || {})
  const questionMaxScore = Number(normalized.questionMaxScore || getQuestionAssignedScore(question) || normalized.maxScore || 100) || 100
  return {
    ...normalized,
    questionScore: Number(normalized.questionScore ?? normalized.totalScore ?? 0) || 0,
    questionMaxScore: questionMaxScore || 100
  }
}

function buildEmptyResult(question = {}) {
  const maxScore = getQuestionAssignedScore(question) || 100
  return normalizeDisplayResult({
    totalScore: 0,
    maxScore,
    questionScore: 0,
    questionMaxScore: maxScore,
    grade: 'D',
    dimensions: [],
    aiComment: '本题未作答，按空答案记 0 分。',
    scoringMode: 'empty_zero'
  }, question)
}

function buildDisplayAnswers(answers = [], questionIds = [], examId = '') {
  const answerMap = new Map()
  const normalizedAnswers = Array.isArray(answers) ? answers.filter(Boolean) : []
  normalizedAnswers.forEach((answer, index) => {
    const questionId = String(answer?.questionId || '').trim()
    if (!questionId) return
    answerMap.set(questionId, {
      ...answer,
      questionId,
      questionIndex: Number.isFinite(Number(answer?.questionIndex)) ? Number(answer.questionIndex) : index
    })
  })

  const order = Array.isArray(questionIds) ? questionIds.map((id) => String(id || '').trim()).filter(Boolean) : []
  if (order.length) {
    const ordered = order.map((questionId, index) => {
      const matched = answerMap.get(questionId)
      if (matched) return { ...matched, questionIndex: index }
      return {
        examId,
        questionId,
        questionIndex: index,
        questionStem: '',
        province: 'national',
        transcript: '',
        scoringResult: null,
        answerTiming: null,
        isPlaceholder: true
      }
    })
    const appended = normalizedAnswers.filter((answer) => !order.includes(String(answer?.questionId || '').trim()))
    return [...ordered, ...appended]
  }

  return normalizedAnswers.sort((a, b) => {
    const aIndex = Number.isFinite(Number(a?.questionIndex)) ? Number(a.questionIndex) : 0
    const bIndex = Number.isFinite(Number(b?.questionIndex)) ? Number(b.questionIndex) : 0
    return aIndex - bIndex
  })
}

async function hydrateMissingQuestionInfo(items = []) {
  await Promise.all(items.map(async (answer) => {
    if (!answer?.questionId || answer.questionStem) return
    try {
      const question = await getQuestionById(answer.questionId)
      if (!question?.id) return
      answer.questionStem = question.stem || ''
      answer.province = question.province || answer.province || 'national'
      answer.scoringResult = answer.scoringResult
        ? normalizeDisplayResult(answer.scoringResult, question)
        : buildEmptyResult(question)
    } catch {
      answer.scoringResult = answer.scoringResult
        ? normalizeDisplayResult(answer.scoringResult)
        : buildEmptyResult()
    }
  }))
}

function applyAnswer(answer = {}) {
  const scoring = answer.scoringResult || buildEmptyResult()
  result.value = normalizeDisplayResult(scoring)
  transcript.value = answer.transcript || (answer.isPlaceholder ? '未作答' : '')
  questionStem.value = answer.questionStem || ''
  questionProvince.value = answer.province || questionProvince.value || 'national'
  answerTiming.value = answer.answerTiming || result.value?.answerTiming || null
  activeQuestionId.value = String(answer.questionId || activeQuestionId.value || '')
}

function selectAnswer(index) {
  const nextIndex = Math.max(0, Math.min(Number(index) || 0, Math.max(answerList.value.length - 1, 0)))
  activeAnswerIndex.value = nextIndex
  applyAnswer(answerList.value[nextIndex])
  finalizeLoadedResult()
}

function formatAnswerScore(answer = {}) {
  if (answer.isPlaceholder || !answer.scoringResult) return '未作答'
  const scoring = normalizeDisplayResult(answer.scoringResult)
  const score = Number(scoring.questionScore ?? scoring.totalScore ?? 0) || 0
  const maxScore = Number(scoring.questionMaxScore ?? scoring.maxScore ?? 100) || 100
  return `${score}/${maxScore}分`
}

onLoad(async (query) => {
  if (!requireLogin()) return
  await loadResult(query || {})
})

async function loadResult(query) {
  const examId = query.examId || examStore.examId
  const requestedQuestionId = String(query.questionId || '').trim()
  const questionId = requestedQuestionId || examStore.currentQuestion?.id
  const answer = examStore.answers.find((item) => item.questionId === questionId) || examStore.answers[examStore.answers.length - 1]
  activeExamId.value = String(examId || answer?.examId || '')
  activeQuestionId.value = String(questionId || answer?.questionId || '')

  if (examStore.answers.length > 0) {
    const displayAnswers = buildDisplayAnswers(examStore.answers, examStore.questions.map((item) => item.id), activeExamId.value)
    await hydrateMissingQuestionInfo(displayAnswers)
    answerList.value = displayAnswers
    const selectedIndex = Math.max(0, displayAnswers.findIndex((item) => item.questionId === activeQuestionId.value))
    activeAnswerIndex.value = selectedIndex
    applyAnswer(displayAnswers[selectedIndex])
    finalizeLoadedResult()
    return
  }

  showLoading('加载结果')
  try {
    if (examId) {
      const detail = await getHistoryDetail(examId)
      const answers = Array.isArray(detail?.answers) ? detail.answers : []
      const questionIds = Array.isArray(detail?.questionIds) ? detail.questionIds : []
      const displayAnswers = buildDisplayAnswers(answers, questionIds, examId)
      await hydrateMissingQuestionInfo(displayAnswers)
      answerList.value = displayAnswers
      activeExamId.value = String(detail?.examId || examId || '')
      questionProvince.value = detail?.province || questionProvince.value || 'national'

      if (displayAnswers.length) {
        const selectedId = requestedQuestionId
          || (answers.length ? String(answers[answers.length - 1]?.questionId || '') : '')
          || displayAnswers[0].questionId
        const selectedIndex = Math.max(0, displayAnswers.findIndex((item) => item.questionId === selectedId))
        activeAnswerIndex.value = selectedIndex
        applyAnswer(displayAnswers[selectedIndex])
        finalizeLoadedResult()
        return
      }

      result.value = normalizeResult(detail)
      questionStem.value = detail?.questionSummary || ''
      finalizeLoadedResult()
      return
    }

    if (questionId && answer?.scoringResult) {
      answerList.value = [answer]
      activeAnswerIndex.value = 0
      applyAnswer(answer)
      finalizeLoadedResult()
    }
  } catch (error) {
    if (examId && requestedQuestionId) {
      try {
        result.value = normalizeResult(await getScoringResult(examId, requestedQuestionId))
        await hydrateResultContext(examId, requestedQuestionId)
        answerList.value = [{
          examId,
          questionId: requestedQuestionId,
          questionStem: questionStem.value,
          province: questionProvince.value,
          transcript: transcript.value,
          scoringResult: result.value,
          answerTiming: answerTiming.value
        }]
        finalizeLoadedResult()
        return
      } catch {
        // Fall through to the user-facing load failure below.
      }
    }
    toast(error?.message || '结果加载失败')
  } finally {
    hideLoading()
  }
}

async function hydrateResultContext(examId, questionId) {
  try {
    const detail = await getHistoryDetail(examId)
    applyHistoryDetailContext(detail, questionId)
  } catch {
    // Scoring results can exist briefly before history detail is ready.
  }
}

function applyHistoryDetailContext(detail = {}, questionId = '') {
  activeExamId.value = String(detail?.examId || activeExamId.value || '')
  questionProvince.value = detail?.province || questionProvince.value || 'national'
  const answers = Array.isArray(detail?.answers) ? detail.answers : []
  const matchedAnswer = answers.find((item) => item.questionId === questionId) || answers[0]
  if (!matchedAnswer) return
  activeQuestionId.value = String(matchedAnswer.questionId || activeQuestionId.value || '')
  questionProvince.value = matchedAnswer.province || detail?.province || questionProvince.value || 'national'
  if (!transcript.value) transcript.value = matchedAnswer.transcript || ''
  if (!questionStem.value) questionStem.value = matchedAnswer.questionStem || detail?.questionSummary || ''
  if (!answerTiming.value) {
    answerTiming.value = matchedAnswer.answerTiming || matchedAnswer.scoringResult?.answerTiming || null
  }
}

function finalizeLoadedResult() {
  recordTrainingProgress()
  recordWeakFavorite()
}

function recordTrainingProgress() {
  const source = String(examStore.source || '')
  if (progressRecorded.value || !source.startsWith('training:') || !result.value) return
  const key = source.replace('training:', '')
  trainingStore.recordResult(key, result.value.totalScore)
  progressRecorded.value = true
}

function recordWeakFavorite() {
  if (currentAnswer.value?.isPlaceholder) return
  if (!result.value || !activeExamId.value || !activeQuestionId.value) return
  if (weakRecordedQuestionIds.value.has(activeQuestionId.value)) return
  const score = Number(result.value.totalScore || 0)
  const maxScore = Number(result.value.maxScore || 100)
  if (!Number.isFinite(score) || !Number.isFinite(maxScore) || maxScore <= 0 || score / maxScore >= 0.6) return
  weakRecordedQuestionIds.value.add(activeQuestionId.value)
  favoritesStore.addItem({
    examId: activeExamId.value,
    questionId: activeQuestionId.value,
    questionStem: questionStem.value || '题目内容暂缺',
    dimension: result.value.dimensions?.[0]?.name || '',
    score,
    maxScore,
    grade: grade.value.label,
    date: new Date().toISOString(),
    type: 'weak'
  })
}

function toggleStarred() {
  if (currentAnswer.value?.isPlaceholder) {
    toast('未作答题目暂时无法收藏')
    return
  }
  if (!result.value || !activeExamId.value || !activeQuestionId.value) {
    toast('题目信息不完整，暂时无法收藏')
    return
  }
  const item = favoritesStore.items.find((entry) => (
    entry.examId === activeExamId.value && entry.questionId === activeQuestionId.value
  ))
  if (isStarred.value && item) {
    favoritesStore.removeItem(item.id, 'starred')
    toast('已取消收藏')
    return
  }
  favoritesStore.addItem({
    examId: activeExamId.value,
    questionId: activeQuestionId.value,
    questionStem: questionStem.value || '题目内容暂缺',
    dimension: result.value.dimensions?.[0]?.name || '',
    score: result.value.totalScore,
    maxScore: result.value.maxScore,
    grade: grade.value.label,
    date: new Date().toISOString(),
    type: 'starred'
  })
  toast('已收藏', 'success')
}

function openShareCard() {
  shareVisible.value = true
}

function closeShareCard() {
  shareVisible.value = false
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
  color: #64748B;
  font-size: 24rpx;
}

.result-hero__score {
  margin-top: 8rpx;
  color: #172033;
  font-size: 52rpx;
  font-weight: 900;
}

.result-hero__grade {
  margin-top: 4rpx;
  font-size: 28rpx;
  font-weight: 800;
}

.answer-tabs {
  padding: 22rpx 24rpx;
}

.answer-tabs__summary {
  display: block;
  margin-bottom: 14rpx;
  color: #64748B;
  font-size: 24rpx;
  font-weight: 700;
}

.answer-tabs__scroll {
  width: 100%;
  white-space: nowrap;
}

.answer-tabs__row {
  display: flex;
  gap: 12rpx;
}

.answer-tab {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  min-width: 172rpx;
  height: 64rpx;
  margin: 0;
  padding: 0 18rpx;
  border: 2rpx solid #D7E4F2;
  border-radius: 8rpx;
  background: #FFFFFF;
  color: #2A3648;
  font-size: 24rpx;
  font-weight: 800;
  line-height: 1;
  white-space: nowrap;
}

.answer-tab--active {
  border-color: #2F7FD6;
  background: #EAF5FF;
  color: #1B5FAA;
}

.answer-tab--empty {
  border-color: #E2E8F0;
  background: #F8FAFC;
  color: #8A97A8;
}

.plain-text {
  color: #2a3648;
  font-size: 27rpx;
  line-height: 1.75;
  white-space: pre-wrap;
}

.local-fit-card__tags {
  display: flex;
  flex-wrap: wrap;
  gap: 12rpx;
}

.local-fit-card__tag {
  display: block;
  padding: 8rpx 14rpx;
  border-radius: 999rpx;
  background: #EAF5FF;
  color: #2F7FD6;
  font-size: 23rpx;
  font-weight: 800;
}

.local-fit-card__desc {
  display: block;
  margin-top: 14rpx;
  color: #2a3648;
  font-size: 26rpx;
  line-height: 1.7;
}

.timing-card__main,
.timing-card__overtime,
.transcript-status-card__title,
.transcript-status-card__desc {
  display: block;
}

.timing-card__main {
  color: #172033;
  font-size: 28rpx;
  font-weight: 800;
}

.timing-card__overtime {
  margin-top: 10rpx;
  color: #d4380d;
  font-size: 25rpx;
  font-weight: 800;
}

.transcript-status-card__title {
  color: #172033;
  font-size: 28rpx;
  font-weight: 900;
}

.transcript-status-card__desc {
  margin-top: 10rpx;
  color: #64748B;
  font-size: 25rpx;
  line-height: 1.65;
}

.ai-generated-note {
  display: block;
  margin: -2rpx 0 14rpx;
  color: #8a97a8;
  font-size: 22rpx;
  line-height: 1.45;
}

.improvement-card__source {
  padding: 6rpx 12rpx;
  border-radius: 999rpx;
  background: #EAF5FF;
  color: #2F7FD6;
  font-size: 22rpx;
  font-weight: 800;
}

.improvement-card__summary,
.teacher-note__label,
.teacher-note__text,
.suggestion-block__title,
.suggestion-line,
.rewrite-line,
.sample-answer,
.focus-item__title,
.focus-item__hint,
.upgrade-item__before,
.upgrade-item__after {
  display: block;
}

.improvement-card__summary {
  color: #1f2b3d;
  font-size: 28rpx;
  font-weight: 800;
  line-height: 1.6;
}

.teacher-note {
  margin-top: 18rpx;
  padding: 18rpx;
  border-left: 6rpx solid #2F7FD6;
  border-radius: 12rpx;
  background: #f4f8fd;
}

.teacher-note__label {
  color: #2F7FD6;
  font-size: 23rpx;
  font-weight: 800;
}

.teacher-note__text {
  margin-top: 8rpx;
  color: #2a3648;
  font-size: 26rpx;
  line-height: 1.7;
}

.suggestion-block {
  margin-top: 22rpx;
}

.suggestion-block__title {
  margin-bottom: 12rpx;
  color: #172033;
  font-size: 27rpx;
  font-weight: 900;
}

.suggestion-line {
  margin-top: 10rpx;
  padding: 14rpx 16rpx;
  border-radius: 12rpx;
  background: #f7f9fc;
  color: #2a3648;
  font-size: 25rpx;
  line-height: 1.6;
}

.focus-item {
  display: flex;
  gap: 14rpx;
  margin-top: 12rpx;
  padding: 16rpx;
  border: 1rpx solid #e7eef7;
  border-radius: 12rpx;
}

.focus-item__order {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 44rpx;
  height: 44rpx;
  border-radius: 50%;
  background: #2F7FD6;
  color: #ffffff;
  font-size: 23rpx;
  font-weight: 900;
}

.focus-item__copy {
  flex: 1;
  min-width: 0;
}

.focus-item__title {
  color: #172033;
  font-size: 26rpx;
  font-weight: 800;
}

.focus-item__hint {
  margin-top: 6rpx;
  color: #5f6f83;
  font-size: 24rpx;
  line-height: 1.6;
}

.rewrite-line,
.sample-answer {
  padding: 16rpx;
  border-radius: 12rpx;
  background: #fffaf0;
  color: #3f2b12;
  font-size: 25rpx;
  line-height: 1.7;
}

.keyword-row {
  display: flex;
  flex-wrap: wrap;
  gap: 10rpx;
}

.keyword-chip {
  padding: 7rpx 14rpx;
  border-radius: 999rpx;
  background: #fff2e8;
  color: #8a4d17;
  font-size: 23rpx;
  font-weight: 800;
}

.upgrade-item {
  display: grid;
  gap: 10rpx;
  margin-top: 12rpx;
  padding: 16rpx;
  border-radius: 12rpx;
  background: #f7f9fc;
}

.upgrade-item__before {
  color: #8a97a8;
  font-size: 24rpx;
  line-height: 1.6;
}

.upgrade-item__after {
  color: #1f2b3d;
  font-size: 25rpx;
  font-weight: 800;
  line-height: 1.6;
}

.utility-actions {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 16rpx;
}

.result-actions {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 16rpx;
}

.share-mask {
  position: fixed;
  z-index: 900;
  inset: 0;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 42rpx;
  background: rgba(9, 24, 42, 0.54);
}

.share-panel {
  width: 100%;
  max-width: 640rpx;
  padding: 24rpx;
  border-radius: 18rpx;
  background: #ffffff;
}

.share-card {
  overflow: hidden;
  padding: 28rpx;
  border: 1rpx solid #DCEAF7;
  border-radius: 18rpx;
  background: linear-gradient(135deg, #ffffff 0%, #EAF5FF 58%, #DFF0FF 100%);
  color: #172033;
}

.share-card__header,
.share-card__dim {
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.share-card__header {
  opacity: 0.86;
  font-size: 23rpx;
}

.share-card__score {
  margin-top: 30rpx;
  text-align: center;
  font-size: 86rpx;
  font-weight: 900;
  line-height: 1;
}

.share-card__label,
.share-card__grade,
.share-card__slogan {
  display: block;
  text-align: center;
}

.share-card__label {
  margin-top: 8rpx;
  opacity: 0.82;
  font-size: 24rpx;
}

.share-card__grade {
  margin-top: 8rpx;
  font-size: 30rpx;
  font-weight: 900;
}

.share-card__dims {
  display: grid;
  gap: 10rpx;
  margin-top: 28rpx;
}

.share-card__dim {
  padding: 12rpx 14rpx;
  border-radius: 12rpx;
  background: rgba(47, 127, 214, 0.08);
  font-size: 23rpx;
}

.share-card__slogan {
  margin-top: 24rpx;
  opacity: 0.82;
  font-size: 23rpx;
}

.share-panel .primary-button {
  margin-top: 22rpx;
}

.share-panel__close {
  margin-top: 12rpx;
}
</style>
