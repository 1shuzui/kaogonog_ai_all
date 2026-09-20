<!--
小程序结果页，展示评分后的总分、能力维度、文字稿、扣分分析、建议和历史保存状态。

这里是评分后页面，可以展示分数和诊断；考场页不能提前暴露这些内容。能力维度与训练题型分类保持分离，
数据不足时宁可隐藏图表，也不要用题型分类硬凑能力雷达。

@param: 无；结果来自 exam store、路由参数或历史结果接口。
@return: 渲染评分结果、复盘内容、重练/分享入口和异常空态。
@raises: 不主动抛业务异常；结果缺失、接口失败或分享失败由页面提示承接。
-->
<template>
  <view class="motion-page page learner-page learner-result" :class="motionClass" :style="motionStyle">
    <MotionSummary class="result-motion-summary" :compact="compact && !!result" :title="currentQuestionLabel" :detail="result ? `${result.totalScore} / ${result.maxScore} 分` : ''" />
    <view class="learner-kicker"><LearnerIcon name="solution" :size="20" /><text>练习复盘</text></view>
    <text class="learner-title">这次作答，下一步怎么练。</text>
    <BackgroundAnswers @layout-change="calibrate" />
    <view v-if="answerList.length > 1" class="card answer-tabs">
      <text class="answer-tabs__summary">已答 {{ completedAnswerCount }} 题，未答 {{ unansweredCount }} 题</text>
      <scroll-view scroll-x class="answer-tabs__scroll" :scroll-into-view="`result-answer-${activeAnswerIndex}`">
        <view class="answer-tabs__row" role="tablist" aria-label="选择查看的题目">
          <button v-for="(item, index) in answerList" :key="item.questionId || index"
            :id="`result-answer-${index}`" role="tab" :aria-selected="index === activeAnswerIndex"
            class="answer-tab" :class="{ 'answer-tab--active': index === activeAnswerIndex, 'answer-tab--empty': item.isPlaceholder }"
            @tap="selectAnswer(index)">
            第 {{ index + 1 }} 题 {{ formatAnswerScore(item) }}
          </button>
        </view>
      </scroll-view>
    </view>
    <template v-if="result">
      <view class="result-hero card">
        <view class="result-hero__copy">
          <text class="result-hero__kicker">{{ currentAnswer?.isPlaceholder ? '未作答记录' : '模型评测结果' }} · {{ currentQuestionLabel }}</text>
          <text class="result-hero__score">{{ result.totalScore }}/{{ result.maxScore }} 分</text>
          <text class="result-hero__grade">{{ grade.label }}</text>
        </view>
        <ScoreRing :score="result.totalScore" :max-score="result.maxScore" size="medium" :color="grade.color" label="" />
      </view>

      <view class="card review-priorities">
        <view class="section-head"><LearnerIcon name="aim" /><text class="section-title">本题改进重点</text></view>
        <text v-if="reviewPriorities.length" class="ai-generated-note">摘自本题已有模型建议，最多展示 3 项，仅供训练参考。</text>
        <view v-for="(item, index) in reviewPriorities" :key="`${index}-${item.title}`" class="review-priority">
          <text class="review-priority__number">{{ index + 1 }}</text>
          <view class="review-priority__copy">
            <text v-if="item.title" class="review-priority__title">{{ item.title }}</text>
            <text v-if="item.text" class="plain-text">{{ item.text }}</text>
          </view>
        </view>
        <text v-if="!reviewPriorities.length" class="plain-text">本次结果未提供可直接执行的具体建议。可展开原文与完整点评复盘，不根据分数推测短板。</text>
      </view>

      <view class="card review-next-action">
        <text class="section-title">下一步</text>
        <text class="review-next-action__hint">{{ reviewPriorities.length ? '先对照原文复盘，再带着本题已有建议继续练习。' : '可展开完整作答记录复盘，或继续练习。' }}</text>
        <view class="result-actions">
          <button class="primary-button" @tap="again">继续练习</button>
          <button class="secondary-button" @tap="home">返回首页</button>
        </view>
      </view>

      <button class="review-toggle" :aria-expanded="detailsOpen" aria-controls="result-review-details" @tap="detailsOpen = !detailsOpen">
        <text class="review-toggle__title">原文、题目与完整点评</text>
        <text>{{ detailsOpen ? '收起' : '展开' }}</text>
        <view class="review-toggle__arrow" :class="{ 'review-toggle__arrow--open': detailsOpen }"><LearnerIcon name="arrow-right" :size="18" /></view>
      </button>
      <MotionCollapse id="result-review-details" :open="detailsOpen" :revision="reviewRevision" @settled="calibrate">
      <view v-if="displayTranscript" class="card learner-transcript">
        <view class="section-head"><LearnerIcon name="file-text" /><text class="section-title">我的作答原文</text></view>
        <text class="plain-text" selectable>{{ displayTranscript }}</text>
      </view>
      <view v-else-if="noContentReason" class="card transcript-status-card">
        <text class="section-title">我的作答原文</text>
        <text class="transcript-status-card__title">{{ noContentReason.title }}</text>
        <text class="transcript-status-card__desc">{{ noContentReason.desc }}</text>
      </view>

      <view class="card">
        <text class="section-title">评分口径</text>
        <text class="plain-text">依据本题采分点、题库参考答案与实际作答评估；能力条采用内容百分制权重，不与题目赋分直接相加。历史总评换算为百分制，整套仪态分仅计一次。</text>
        <text v-if="result.contentScore != null" class="plain-text">内容 {{ result.contentScore }} / {{ result.contentMaxScore || (result.maxScore - result.appearanceScoreMax) }}；仪态 {{ result.appearanceScore }} / {{ result.appearanceScoreMax }}。{{ result.scoreCalculationNote }}</text>
        <text class="plain-text">等级按得分率：A ≥85%，B ≥75%，C ≥60%，其余为 D。AI 结果仅供训练参考，不代表官方考试成绩。</text>
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

      <view v-if="answerVideoUrl" class="card">
        <text class="section-title">作答录像回放</text>
        <video v-if="visible" :key="activeQuestionId" :src="answerVideoUrl" controls class="answer-video" @loadedmetadata="mediaRevision += 1" />
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
          <text class="teacher-note__label">补充评语</text>
          <text class="teacher-note__text">{{ improvementSuggestion.teacherComment }}</text>
        </view>

        <view v-if="improvementSuggestion.diagnosisItems.length" class="suggestion-block">
          <text class="suggestion-block__title">{{ improvementSuggestion.source === 'model' ? '主要影响得分的地方' : '通用复盘检查项' }}</text>
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
          <text class="suggestion-block__title">建议示范改写（非我的作答）</text>
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
      </MotionCollapse>

      <view class="utility-actions card">
        <button class="secondary-button" @tap="toggleStarred">
          {{ isStarred ? '已收藏' : '收藏本题' }}
        </button>
        <button class="secondary-button" @tap="openShareCard">分享成绩卡</button>
      </view>

      <view v-if="shareVisible && visible" class="share-mask" @tap="closeShareCard">
        <view class="share-panel" @tap.stop>
          <view class="share-card">
            <view class="share-card__header">
              <text>公考面试AI智能测评</text>
              <text>{{ shareDate }}</text>
            </view>
            <view class="share-card__score">{{ result.totalScore }}</view>
            <text class="share-card__label">综合得分 / {{ result.maxScore }} 分</text>
            <text class="share-card__grade">{{ grade.label }}</text>
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
    <view v-else-if="currentAnswer && !currentAnswer.isPlaceholder" class="card">
      <view class="section-head"><text class="section-title">{{ currentAnswer.processingStatus === 'failed' ? '处理未完成，可重试' : '作答已收到 · 待点评' }}</text></view>
      <text v-if="!displayTranscript" class="plain-text">{{ currentAnswer.processingStatus === 'failed' ? '文字稿尚未生成，请重试录音处理。' : '录音正在处理，文字稿和点评完成后会自动显示。请保持小程序打开。' }}</text>
      <text class="plain-text" selectable>{{ displayTranscript }}</text>
      <text v-if="currentAnswer.processingError" class="plain-text">{{ currentAnswer.processingError }}</text>
      <video v-if="answerVideoUrl && visible" :key="activeQuestionId" :src="answerVideoUrl" controls class="answer-video" />
      <button v-if="canRetryCurrentAnswer" class="primary-button" :loading="retryingScoring" :disabled="retryingScoring" @tap="retryScoring">
        {{ retryingScoring ? '正在处理' : '重试处理' }}
      </button>
      <button v-if="retryingScoring" class="secondary-button" @tap="cancelScoringRetry">停止等待</button>
      <text v-if="retryNotice" class="review-notice" role="status">{{ retryNotice }}</text>
      <text v-if="retryingScoring" class="review-notice">停止等待不会撤回已提交的后台处理；原文和录音保留。</text>
      <button class="secondary-button" @tap="home">返回首页</button>
    </view>
    <view v-else-if="loadingResult" class="card" role="status" aria-busy="true">
      <text class="section-title">正在读取本次结果</text>
      <text class="plain-text">读取已保存的作答和点评，不会重新评分。</text>
    </view>
    <view v-else-if="loadError" class="card">
      <text class="section-title">结果暂未读到</text>
      <text class="plain-text">{{ loadError }}</text>
      <button class="primary-button" @tap="loadResult(lastQuery)">重新加载</button>
      <button class="secondary-button" @tap="home">返回首页</button>
    </view>
    <view v-else class="card">
      <EmptyState title="暂无评分结果" desc="如果刚提交作答，请稍后刷新历史记录。" />
    </view>
  </view>
</template>

<script setup>
import MotionSummary from '../../components/MotionSummary.vue'
import MotionCollapse from '../../components/MotionCollapse.vue'
import { useScrollSummary } from '../../motion/useScrollSummary'
import { onPageScroll } from '@dcloudio/uni-app'
import { usePageMotion } from '../../motion/useMotion'
const { motionClass, motionStyle, visible } = usePageMotion()
import LearnerIcon from '../../components/LearnerIcon.vue'
import { computed, ref, watch } from 'vue'
import { onLoad, onUnload, onShareAppMessage } from '@dcloudio/uni-app'
import DimensionBars from '../../components/DimensionBars.vue'
import EmptyState from '../../components/EmptyState.vue'
import ScoreRing from '../../components/ScoreRing.vue'
import BackgroundAnswers from '../../components/BackgroundAnswers.vue'
import { API_BASE, request } from '../../api/request'
import { useExamStore } from '../../stores/exam'
import { useFavoritesStore } from '../../stores/favorites'
import { useTrainingStore } from '../../stores/training'
import { getGrade, getProvinceName } from '../../utils/constants'
import { requireLogin, toast } from '../../utils/navigation'
import { canUseLocalAnswers } from '../../utils/resultAnswerSource'
import { hasFinalScore } from '../../utils/answerStatus'
import { getQuestionScorePair } from '../../utils/scorePresentation'
import { normalizeResult } from '../../utils/scoring'
import { createCancellation } from '../../utils/cancellation.mjs'
import { readReviewSuggestion, getReviewPriorities, getReviewTranscript } from '../../utils/resultReview.mjs'

const examStore = useExamStore()
const favoritesStore = useFavoritesStore()
const trainingStore = useTrainingStore()
const result = ref(null)
const { compact, calibrate, onSummaryScroll } = useScrollSummary('.result-hero', () => result.value)
onPageScroll(onSummaryScroll)
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
const retryingScoring = ref(false)
const loadingResult = ref(false)
const loadError = ref('')
const retryNotice = ref('')
const detailsOpen = ref(false)
const mediaRevision = ref(0)
let loadRequest = null
let retryRequest = null
let disposed = false
let lastQuery = {}

const grade = computed(() => getGrade(result.value?.totalScore || 0, result.value?.maxScore || 100))
const localFitProvinceName = computed(() => getProvinceName(questionProvince.value || 'national'))
const currentAnswer = computed(() => answerList.value[activeAnswerIndex.value] || null)
const canRetryCurrentAnswer = computed(() => currentAnswer.value?.processingStatus === 'failed'
  || (!currentAnswer.value?.processingStatus && !!displayTranscript.value && !result.value))
const answerVideoUrl = computed(() => {
  const answer = currentAnswer.value || {}
  const media = result.value?.mediaRecord || answer.scoringResult?.mediaRecord || {}
  const type = String(media.mediaType || answer.mediaType || '')
  if (!type.includes('video')) return ''
  const url = media.fileUrl || answer.mediaUrl || answer.filePath || ''
  return url.startsWith('/uploads/') ? `${API_BASE}${url}` : url
})
const currentQuestionLabel = computed(() => (
  answerList.value.length > 1
    ? `第 ${activeAnswerIndex.value + 1} 题${currentAnswer.value?.isPlaceholder ? ' · 未作答' : ''}`
    : currentAnswer.value?.isPlaceholder ? '本题 · 未作答' : '本题'
))
const completedAnswerCount = computed(() => answerList.value.filter((answer) => !answer?.isPlaceholder).length)
const unansweredCount = computed(() => answerList.value.filter((answer) => answer?.isPlaceholder).length)
const improvementSuggestion = computed(() => {
  if (currentAnswer.value?.isPlaceholder || isNoContentTranscript(transcript.value, result.value)) return null
  return readReviewSuggestion(result.value?.answerImprovementSuggestion)
})
const reviewPriorities = computed(() => getReviewPriorities(improvementSuggestion.value))
const suggestionSourceLabel = computed(() => (
  improvementSuggestion.value?.source === 'model' ? '模型建议' : '通用参考，非本题诊断'
))
const displayTranscript = computed(() => getReviewTranscript(transcript.value))
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
const reviewRevision = computed(() => [activeQuestionId.value, result.value, displayTranscript.value, questionStem.value, questionProvince.value, answerTimingView.value, answerVideoUrl.value, mediaRevision.value])

function isCurrentLoad(task) {
  return !disposed && loadRequest === task && !task.signal.aborted
}

function cancelResultLoad() {
  const task = loadRequest
  loadRequest = null
  task?.cancel()
  loadingResult.value = false
}

function cancelScoringRetry() {
  const task = retryRequest
  retryRequest = null
  task?.cancel()
  retryingScoring.value = false
  if (task) retryNotice.value = '已停止本页等待，原文和录音保留；已提交的后台处理可能仍会完成。'
}

// Store-owned media processing remains alive across pages; only this page's wait ends.
async function waitForPageTask(promise, task) {
  let unsubscribe
  try {
    return await Promise.race([promise, new Promise(resolve => {
      unsubscribe = task.signal.subscribe(() => resolve(null))
    })])
  } finally {
    unsubscribe?.()
  }
}

watch(visible, shown => {
  if (shown) { syncLocalAnswers(); calibrate(); return }
  if (loadingResult.value) loadError.value = '加载已暂停，请重新加载结果。'
  cancelResultLoad()
  cancelScoringRetry()
  shareVisible.value = false
}, { flush: 'sync' })
onUnload(() => { disposed = true; cancelResultLoad(); cancelScoringRetry() })

onShareAppMessage(() => ({
  title: result.value ? `我的面试测评得分 ${result.value.totalScore}/${result.value.maxScore}` : '面试练习复盘 · 待点评',
  path: sharePath.value
}))

function isNoContentTranscript(value, scoring = {}) {
  const text = String(value || '').trim()
  const mode = String(scoring?.scoringMode || '').trim()
  return text ? !getReviewTranscript(value) : ['screened_zero', 'empty_zero'].includes(mode)
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

function getQuestionAssignedScore(question = {}) {
  const points = Array.isArray(question?.scoringPoints) ? question.scoringPoints : []
  return points.reduce((sum, item) => sum + (Number(item?.score || 0) || 0), 0)
}

function normalizeDisplayResult(value = {}, question = {}) {
  const normalized = normalizeResult(value || {})
  const questionMaxScore = Number(normalized.questionMaxScore || getQuestionAssignedScore(question) || normalized.maxScore || 100) || 100
  return {
    ...normalized,
    // Keep supplied feedback only; score normalization must not manufacture review advice.
    answerImprovementSuggestion: value?.answerImprovementSuggestion || null,
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

async function hydrateMissingQuestionInfo(items = [], task = loadRequest) {
  await Promise.all(items.map(async (answer) => {
    if (!isCurrentLoad(task) || !answer?.questionId || answer.questionStem) return
    try {
      const question = await request({ url: `/questions/${answer.questionId}`, signal: task.signal, skipErrorHandler: true })
      if (!isCurrentLoad(task) || !question?.id) return
      answer.questionStem = question.stem || ''
      answer.province = question.province || answer.province || 'national'
      answer.scoringResult = answer.scoringResult
        ? (hasFinalScore(answer.scoringResult) ? normalizeDisplayResult(answer.scoringResult, question) : null)
        : (answer.isPlaceholder ? buildEmptyResult(question) : null)
    } catch {
      if (!isCurrentLoad(task)) return
      answer.scoringResult = answer.scoringResult
        ? (hasFinalScore(answer.scoringResult) ? normalizeDisplayResult(answer.scoringResult) : null)
        : (answer.isPlaceholder ? buildEmptyResult() : null)
    }
  }))
}

function applyAnswer(answer = {}) {
  const scoring = answer.isPlaceholder ? buildEmptyResult() : answer.scoringResult
  result.value = hasFinalScore(scoring) ? normalizeDisplayResult(scoring) : null
  transcript.value = answer.transcript || (answer.isPlaceholder ? '未作答' : '')
  questionStem.value = answer.questionStem || ''
  questionProvince.value = answer.province || questionProvince.value || 'national'
  answerTiming.value = answer.answerTiming || result.value?.answerTiming || null
  activeQuestionId.value = String(answer.questionId || activeQuestionId.value || '')
}

function selectAnswer(index) {
  const nextIndex = Math.max(0, Math.min(Number(index) || 0, Math.max(answerList.value.length - 1, 0)))
  cancelResultLoad()
  cancelScoringRetry()
  retryNotice.value = ''
  if (nextIndex !== activeAnswerIndex.value) detailsOpen.value = false
  shareVisible.value = false
  activeAnswerIndex.value = nextIndex
  applyAnswer(answerList.value[nextIndex])
  finalizeLoadedResult()
}

function formatAnswerScore(answer = {}) {
  if (answer.isPlaceholder) return '未作答'
  if (!hasFinalScore(answer.scoringResult)) return '待点评'
  const scoring = normalizeDisplayResult(answer.scoringResult)
  const { score, maxScore } = getQuestionScorePair(scoring)
  return `${score}/${maxScore}分`
}

onLoad(async (query) => {
  if (!requireLogin()) return
  await loadResult(query || {})
})

watch(() => examStore.getAnswersForExam(activeExamId.value).map((answer) => [answer.questionId, answer.questionIndex, answer.processingStatus, answer.processingError, answer.transcript, answer.scoringResult]), syncLocalAnswers)

function syncLocalAnswers() {
  if (disposed || !visible.value) return
  const localAnswers = examStore.getAnswersForExam(activeExamId.value)
  if (!canUseLocalAnswers(activeExamId.value, activeExamId.value, localAnswers)) return
  const selectedId = activeQuestionId.value
  const previous = answerList.value
  const localById = new Map(localAnswers.map(answer => [answer.questionId, answer]))
  const merged = previous.map(answer => {
    const local = localById.get(answer.questionId)
    return local ? { ...answer, ...local, isPlaceholder: !!local.isPlaceholder } : answer
  })
  for (const answer of localAnswers) {
    if (!previous.some(item => item.questionId === answer.questionId)) merged.push(answer)
  }
  const questionIds = activeExamId.value === examStore.examId && examStore.questions.length
    ? examStore.questions.map(item => item.id) : merged.map(item => item.questionId)
  cancelResultLoad()
  answerList.value = buildDisplayAnswers(merged, questionIds, activeExamId.value).map(answer => {
    const old = previous.find(item => item.questionId === answer.questionId)
    const question = examStore.questions.find(item => item.id === answer.questionId)
    return { ...answer, questionStem: answer.questionStem || old?.questionStem || question?.stem || '', province: answer.province || old?.province || question?.province }
  })
  const selectedIndex = answerList.value.findIndex(answer => answer.questionId === selectedId)
  activeAnswerIndex.value = selectedIndex >= 0 ? selectedIndex : Math.min(activeAnswerIndex.value, Math.max(0, answerList.value.length - 1))
  applyAnswer(answerList.value[activeAnswerIndex.value])
  finalizeLoadedResult()
}

async function loadResult(query) {
  if (disposed) return
  cancelResultLoad()
  cancelScoringRetry()
  lastQuery = { ...query }
  const task = createCancellation()
  loadRequest = task
  loadingResult.value = true
  loadError.value = ''
  retryNotice.value = ''
  detailsOpen.value = false
  shareVisible.value = false
  result.value = null
  transcript.value = ''
  questionStem.value = ''
  answerTiming.value = null
  answerList.value = []
  activeAnswerIndex.value = 0
  const examId = String(query.examId || examStore.examId || '').trim()
  const localAnswers = examStore.getAnswersForExam(examId)
  const canUseLocalExamAnswers = canUseLocalAnswers(examId, examId, localAnswers)
  const requestedQuestionId = String(query.questionId || '').trim()
  const questionId = requestedQuestionId || (canUseLocalExamAnswers ? examStore.currentQuestion?.id : '')
  const answer = canUseLocalExamAnswers
    ? (localAnswers.find((item) => item.questionId === questionId) || localAnswers[localAnswers.length - 1])
    : null
  activeExamId.value = String(examId || answer?.examId || '')
  activeQuestionId.value = String(questionId || answer?.questionId || '')

  try {
    if (canUseLocalExamAnswers) {
      const questionIds = examId === examStore.examId ? examStore.questions.map((item) => item.id) : localAnswers.map((item) => item.questionId)
      const displayAnswers = buildDisplayAnswers(localAnswers, questionIds, activeExamId.value).map((item) => {
        const question = examStore.questions.find((entry) => entry.id === item.questionId)
        return { ...item, questionStem: item.questionStem || question?.stem || '', province: item.province || question?.province }
      })
      answerList.value = displayAnswers
      const selectedIndex = Math.max(0, displayAnswers.findIndex((item) => item.questionId === activeQuestionId.value))
      activeAnswerIndex.value = selectedIndex
      applyAnswer(displayAnswers[selectedIndex])
      finalizeLoadedResult()
      return
    }
    if (examId) {
      const detail = await request({ url: `/history/${examId}`, signal: task.signal, skipErrorHandler: true })
      if (!isCurrentLoad(task)) return
      const answers = Array.isArray(detail?.answers) ? detail.answers : []
      const questionIds = Array.isArray(detail?.questionIds) ? detail.questionIds : []
      const displayAnswers = buildDisplayAnswers(answers, questionIds, examId)
      await hydrateMissingQuestionInfo(displayAnswers, task)
      if (!isCurrentLoad(task)) return
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

      result.value = detail?.scoringStatus !== 'pending' && hasFinalScore(detail) ? normalizeDisplayResult(detail) : null
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
    if (!isCurrentLoad(task)) return
    if (examId && requestedQuestionId) {
      try {
        const savedResult = await request({ url: `/scoring/result/${examId}/${requestedQuestionId}`, signal: task.signal, skipErrorHandler: true })
        if (!isCurrentLoad(task)) return
        const context = await hydrateResultContext(examId, requestedQuestionId, task)
        if (!isCurrentLoad(task)) return
        result.value = hasFinalScore(savedResult) ? normalizeDisplayResult(savedResult) : null
        answerList.value = [{
          ...context,
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
    if (!isCurrentLoad(task)) return
    loadError.value = error?.message || '结果加载失败，请重试。'
  } finally {
    if (loadRequest === task) {
      loadingResult.value = false
      loadRequest = null
    }
  }
}

async function hydrateResultContext(examId, questionId, task = loadRequest) {
  try {
    const detail = await request({ url: `/history/${examId}`, signal: task.signal, skipErrorHandler: true })
    if (!isCurrentLoad(task)) return null
    return applyHistoryDetailContext(detail, questionId)
  } catch {
    // Scoring results can exist briefly before history detail is ready.
  }
}

async function retryScoring() {
  if (disposed || !visible.value || retryingScoring.value || !canRetryCurrentAnswer.value || !activeExamId.value || !activeQuestionId.value) return
  const answer = currentAnswer.value
  const examId = activeExamId.value
  const questionId = activeQuestionId.value
  const task = createCancellation()
  retryRequest = task
  const isCurrent = () => !disposed && retryRequest === task && !task.signal.aborted && activeExamId.value === examId && activeQuestionId.value === questionId
  retryingScoring.value = true
  retryNotice.value = ''
  try {
    const local = examStore.getAnswersForExam(examId).find((item) => item.questionId === questionId)
    if (local) {
      await waitForPageTask(examStore.retryAnswer(local), task)
      return
    }
    const scored = await waitForPageTask(request({
      url: '/scoring/evaluate', method: 'POST', timeout: 90000, signal: task.signal, skipErrorHandler: true,
      data: { examId, questionId, transcript: displayTranscript.value, answerMeta: answerTiming.value ? { answerTiming: answerTiming.value } : {} }
    }), task)
    if (!isCurrent()) return
    if (!hasFinalScore(scored)) throw new Error('点评尚未完成，请稍后重试')
    if (answer) {
      answer.scoringResult = scored
      answer.processingStatus = 'completed'
      if (currentAnswer.value === answer) applyAnswer(answer)
    } else {
      result.value = normalizeDisplayResult(scored)
    }
    finalizeLoadedResult()
  } catch (error) {
    if (!isCurrent() || error?.code === 'CANCELLED') return
    toast(error?.message || '点评暂未完成，答案已保存')
  } finally {
    if (retryRequest === task) {
      retryingScoring.value = false
      retryRequest = null
    }
  }
}

function applyHistoryDetailContext(detail = {}, questionId = '') {
  activeExamId.value = String(detail?.examId || activeExamId.value || '')
  questionProvince.value = detail?.province || questionProvince.value || 'national'
  const answers = Array.isArray(detail?.answers) ? detail.answers : []
  const matchedAnswer = questionId ? answers.find((item) => item.questionId === questionId) : answers[0]
  if (!matchedAnswer) return
  activeQuestionId.value = String(matchedAnswer.questionId || activeQuestionId.value || '')
  questionProvince.value = matchedAnswer.province || detail?.province || questionProvince.value || 'national'
  if (!transcript.value) transcript.value = matchedAnswer.transcript || ''
  if (!questionStem.value) questionStem.value = matchedAnswer.questionStem || detail?.questionSummary || ''
  if (!answerTiming.value) {
    answerTiming.value = matchedAnswer.answerTiming || matchedAnswer.scoringResult?.answerTiming || null
  }
  return matchedAnswer
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
.learner-result {
  color: var(--ui-text, #203047);
  background: var(--ui-bg, #f7f9fd);
}
.learner-result .learner-kicker { font-size: 14px; color: var(--ui-success, #147d74); }
.learner-result .learner-title { font-size: 24px; line-height: 1.5; color: var(--ui-text, #203047); }
.learner-result .card {
  padding: 16px;
  margin-bottom: 16px;
  border: 1px solid var(--ui-border, #dbe3ee);
  border-radius: 12px;
  background: var(--ui-surface, #fdfefe);
  box-shadow: none;
}
.learner-result .section-head { justify-content: flex-start; flex-wrap: wrap; gap: 8px; }
.learner-result .section-title { display: block; color: var(--ui-text, #203047); font-size: 18px; line-height: 1.5; }
.learner-result button { min-height: 44px; box-sizing: border-box; }
.learner-result button:focus-visible { outline: 2px solid var(--ui-primary, #326be5); outline-offset: 3px; }
.learner-result .primary-button,
.learner-result .secondary-button { padding: 12px; font-size: 16px; line-height: 1.5; }
.learner-result .primary-button { color: #fff; background: var(--ui-primary, #326be5); }
.learner-result .secondary-button { color: var(--ui-link, #285bc7); background: var(--ui-surface, #fdfefe); border-color: var(--ui-border, #dbe3ee); }
.learner-result .card > button { margin-top: 12px; }
.learner-result .result-hero {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  background: var(--ui-soft, #edf3ff);
}
.result-hero__copy { min-width: 0; }
.result-hero__kicker,
.result-hero__score,
.result-hero__grade,
.plain-text { display: block; }
.learner-result .result-hero__kicker { color: var(--ui-muted, #596a80); font-size: 14px; line-height: 1.5; }
.learner-result .result-hero__score { margin-top: 8px; color: var(--ui-link, #285bc7); font-size: 28px; font-weight: 700; overflow-wrap: anywhere; }
.result-hero__grade { margin-top: 4px; color: var(--ui-text, #203047); font-size: 16px; font-weight: 600; }
.answer-tabs__summary { display: block; margin-bottom: 12px; color: var(--ui-muted, #596a80); font-size: 14px; line-height: 1.5; }
.answer-tabs__scroll { width: 100%; white-space: nowrap; }
.answer-tabs__row { display: flex; gap: 8px; padding: 4px; }
.learner-result .answer-tab {
  display: inline-flex;
  flex-shrink: 0;
  align-items: center;
  justify-content: center;
  min-width: 120px;
  min-height: 44px;
  margin: 0;
  padding: 8px 12px;
  border: 1px solid var(--ui-border, #dbe3ee);
  border-radius: 12px;
  color: var(--ui-text, #203047);
  background: var(--ui-surface, #fdfefe);
  font-size: 14px;
  line-height: 1.5;
  white-space: nowrap;
}
.learner-result .answer-tab--empty { color: var(--ui-muted, #596a80); background: var(--ui-bg, #f7f9fd); }
/* Selection wins even for an unanswered question. */
.learner-result .answer-tab--active { color: #fff; background: var(--ui-primary, #326be5); border-color: var(--ui-primary, #326be5); font-weight: 700; }
.learner-result .plain-text {
  color: var(--ui-text, #203047);
  font-size: 16px;
  line-height: 1.8;
  white-space: pre-wrap;
  overflow-wrap: anywhere;
}
.learner-result .plain-text + .plain-text { margin-top: 12px; }
.review-priority { display: flex; align-items: flex-start; gap: 12px; margin-top: 16px; }
.review-priority__number { display: flex; flex-shrink: 0; align-items: center; justify-content: center; width: 28px; height: 28px; border-radius: 50%; color: var(--ui-link, #285bc7); background: var(--ui-soft, #edf3ff); font-size: 14px; font-weight: 700; }
.review-priority__copy { min-width: 0; }
.review-priority__title { display: block; color: var(--ui-text, #203047); font-size: 16px; line-height: 1.6; font-weight: 700; }
.review-next-action__hint,
.review-notice { display: block; margin: 8px 0 16px; color: var(--ui-muted, #596a80); font-size: 14px; line-height: 1.7; }
.review-toggle {
  display: flex;
  align-items: center;
  gap: 8px;
  width: 100%;
  min-height: 44px;
  padding: 12px 0;
  margin-bottom: 12px;
  text-align: left;
  color: var(--ui-link, #285bc7);
  background: transparent;
  font-size: 14px;
  line-height: 1.6;
}
.review-toggle__title { flex: 1; min-width: 0; color: var(--ui-text, #203047); font-size: 16px; font-weight: 700; }
.review-toggle__arrow { display: flex; transform: rotate(90deg); transition: transform var(--motion-arrow) var(--motion-ease); }
.review-toggle__arrow--open { transform: rotate(-90deg); }
.answer-video { display: block; width: 100%; height: 200px; margin-top: 12px; }
.local-fit-card__tags,
.keyword-row { display: flex; flex-wrap: wrap; gap: 8px; }
.local-fit-card__tag,
.keyword-chip,
.improvement-card__source { padding: 4px 8px; border-radius: 999px; background: var(--ui-soft, #edf3ff); color: var(--ui-link, #285bc7); font-size: 14px; line-height: 1.6; }
.local-fit-card__desc,
.transcript-status-card__desc { display: block; margin-top: 8px; color: var(--ui-muted, #596a80); font-size: 14px; line-height: 1.8; }
.timing-card__main,
.transcript-status-card__title { display: block; color: var(--ui-text, #203047); font-size: 16px; line-height: 1.6; font-weight: 600; }
.timing-card__overtime { display: block; margin-top: 8px; color: var(--ui-error, #a52c38); font-size: 14px; line-height: 1.6; }
.ai-generated-note { display: block; margin: 8px 0 12px; color: var(--ui-muted, #596a80); font-size: 14px; line-height: 1.6; }
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
.upgrade-item__after { display: block; color: var(--ui-text, #203047); font-size: 16px; line-height: 1.8; white-space: pre-wrap; overflow-wrap: anywhere; }
.improvement-card__summary,
.suggestion-block__title,
.focus-item__title { font-weight: 600; }
.teacher-note { margin-top: 16px; padding: 12px; border-left: 3px solid var(--ui-primary, #326be5); background: var(--ui-soft, #edf3ff); border-radius: 8px; }
.teacher-note__label { color: var(--ui-link, #285bc7); font-size: 14px; font-weight: 600; }
.teacher-note__text { margin-top: 8px; }
.suggestion-block { margin-top: 16px; }
.suggestion-block__title { margin-bottom: 8px; }
.suggestion-line,
.upgrade-item,
.rewrite-line,
.sample-answer { margin-top: 8px; padding: 12px; border-radius: 8px; background: var(--ui-bg, #f7f9fd); }
.focus-item { display: flex; gap: 12px; margin-top: 12px; padding: 12px; border: 1px solid var(--ui-border, #dbe3ee); border-radius: 8px; }
.focus-item__order { display: flex; flex-shrink: 0; align-items: center; justify-content: center; min-width: 24px; height: 24px; border-radius: 50%; background: var(--ui-soft, #edf3ff); color: var(--ui-link, #285bc7); font-size: 14px; }
.focus-item__copy { flex: 1; min-width: 0; }
.focus-item__hint,
.upgrade-item__before { margin-top: 4px; color: var(--ui-muted, #596a80); font-size: 14px; }
.upgrade-item { display: grid; gap: 8px; }
.utility-actions,
.result-actions { display: grid; grid-template-columns: minmax(0, 1fr) minmax(0, 1fr); gap: 12px; }
.learner-result .utility-actions > button { margin-top: 0; }
.share-mask { position: fixed; z-index: var(--ui-layer-sheet, 2200); inset: 0; display: flex; align-items: center; justify-content: center; padding: 24px; background: rgba(32, 48, 71, .54); }
.share-panel { width: 100%; max-width: 400px; max-height: calc(100vh - 48px); overflow: auto; padding: 16px; border-radius: 12px; background: var(--ui-surface, #fdfefe); }
.share-card { padding: 16px; border: 1px solid var(--ui-border, #dbe3ee); border-radius: 12px; background: var(--ui-soft, #edf3ff); color: var(--ui-text, #203047); }
.share-card__header,
.share-card__dim { display: flex; align-items: center; justify-content: space-between; flex-wrap: wrap; gap: 8px; font-size: 14px; line-height: 1.6; }
.share-card__header { color: var(--ui-muted, #596a80); }
.share-card__score { margin-top: 16px; text-align: center; font-size: 40px; font-weight: 700; }
.share-card__label,
.share-card__grade,
.share-card__slogan { display: block; margin-top: 8px; text-align: center; font-size: 14px; line-height: 1.6; color: var(--ui-muted, #596a80); }
.share-card__grade { color: var(--ui-text, #203047); font-size: 16px; font-weight: 700; }
.share-card__dims { display: grid; gap: 8px; margin-top: 16px; }
.share-card__dim { padding: 8px; background: var(--ui-surface, #fdfefe); border-radius: 8px; }
.share-panel .primary-button,
.share-panel__close { margin-top: 12px; }
@media (max-width: 360px) {
  .learner-result.page { padding-left: 16px; padding-right: 16px; }
  .learner-result .result-hero__score { font-size: 24px; }
  .utility-actions, .result-actions { gap: 8px; }
}
</style>
