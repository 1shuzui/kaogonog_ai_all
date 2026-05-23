const PROVINCE_NAME_TO_CODE = {
  江苏: 'jiangsu',
  安徽: 'anhui',
  安徽消防: 'anhui',
  湖南: 'hunan',
  全国: 'national'
}

const PROVINCE_CODE_TO_NAME = {
  jiangsu: '江苏',
  anhui: '安徽',
  hunan: '湖南',
  national: '全国'
}

const FULL_EXAM_FETCH_PAGE_SIZE = 1000
const MIN_SUITE_QUESTION_COUNT = 2
const JIANGSU_FULL_EXAM_TIMING_MODE = 'jiangsu_5_15'

export function normalizeProvinceCode(value = '') {
  const raw = String(value || '').trim()
  if (!raw) return 'national'
  if (PROVINCE_NAME_TO_CODE[raw]) return PROVINCE_NAME_TO_CODE[raw]

  const lower = raw.toLowerCase()
  if (lower === 'shaanxi') return 'shanxi'
  return lower
}

function normalizeQuestionListResponse(response = {}) {
  if (Array.isArray(response)) return response
  if (Array.isArray(response?.data?.list)) return response.data.list
  if (Array.isArray(response?.data?.items)) return response.data.items
  if (Array.isArray(response?.data)) return response.data

  const list = response?.list || response?.items || response?.records || response?.results || []
  return Array.isArray(list) ? list : []
}

function toNumber(value, fallback = 0) {
  const numeric = Number(value)
  return Number.isFinite(numeric) ? numeric : fallback
}

function firstPositiveNumber(...values) {
  for (const value of values) {
    const numeric = Number(value)
    if (Number.isFinite(numeric) && numeric > 0) return numeric
  }
  return 0
}

function sumDimensionScores(dimensions = []) {
  if (!Array.isArray(dimensions)) return 0
  return dimensions.reduce((sum, item) => (
    sum + firstPositiveNumber(item?.score, item?.maxScore, item?.max_score, item?.points)
  ), 0)
}

function getQuestionId(raw = {}) {
  return String(raw.id || raw.questionId || raw.question_id || '').trim()
}

function getQuestionStem(raw = {}) {
  return String(raw.stem || raw.question || raw.content || '').replace(/^：/, '').trim()
}

function getQuestionScore(raw = {}) {
  return firstPositiveNumber(
    raw.assignedScore,
    raw.questionMaxScore,
    raw.fullScore,
    raw.full_score,
    raw.score,
    raw.maxScore,
    raw.max_score,
    sumDimensionScores(raw.dimensions)
  )
}

function getSourceDocument(raw = {}) {
  return String(raw.sourceDocument || raw.source_document || raw.source || '').trim()
}

function extractSuiteKey(questionId = '') {
  const id = String(questionId || '').trim()
  const match = id.match(/^(.*)-(\d{2,})$/)
  return match ? match[1] : ''
}

function extractQuestionOrder(questionId = '') {
  const match = String(questionId || '').trim().match(/-(\d{2,})$/)
  return match ? Number(match[1]) : Number.MAX_SAFE_INTEGER
}

function isCompleteNumberedSuite(questions = []) {
  if (questions.length < MIN_SUITE_QUESTION_COUNT) return false
  const orders = questions.map((item) => extractQuestionOrder(getQuestionId(item)))
  if (orders.some((order) => !Number.isFinite(order) || order === Number.MAX_SAFE_INTEGER)) return false
  const unique = new Set(orders)
  if (unique.size !== orders.length) return false
  return [...unique].sort((a, b) => a - b).every((order, index) => order === index + 1)
}

function buildSuiteTitle(province, suiteKey) {
  const provinceName = PROVINCE_CODE_TO_NAME[province] || province || '真题'
  return `${provinceName}真题套卷 ${suiteKey}`
}

function buildSortKey(suiteKey = '') {
  const dateMatch = String(suiteKey).match(/20\d{2}(?:\d{2})?(?:\d{2})?/)
  return dateMatch ? dateMatch[0] : suiteKey
}

function normalizeScoringPoints(raw = {}, assignedScore = 0) {
  const existing = Array.isArray(raw.scoringPoints)
    ? raw.scoringPoints
    : Array.isArray(raw.scoring_points)
      ? raw.scoring_points
      : []

  if (existing.length) {
    return existing.map((item) => ({
      ...item,
      content: item.content || item.name || item.dimension || '',
      score: toNumber(item.score, toNumber(item.maxScore, 0))
    }))
  }

  const dimensions = Array.isArray(raw.dimensions) ? raw.dimensions : []
  if (dimensions.length) {
    return dimensions.map((item) => ({
      content: item.name || item.dimension || '采分点',
      score: firstPositiveNumber(item.score, item.maxScore, item.max_score, item.points)
    }))
  }

  return assignedScore > 0 ? [{ content: '本题作答表现', score: assignedScore }] : []
}

export function normalizeFullExamQuestion(raw = {}, suite = {}, index = 0) {
  const assignedScore = getQuestionScore(raw)
  const fullScore = firstPositiveNumber(raw.fullScore, raw.full_score, assignedScore)
  const stem = getQuestionStem(raw)
  const questionId = getQuestionId(raw)
  const questionCount = Array.isArray(suite.questions) ? suite.questions.length : 0

  return {
    ...raw,
    id: questionId,
    stem,
    question: raw.question || stem,
    type: raw.type || raw.dimension || '',
    dimension: raw.dimension || raw.category || raw.type || '',
    province: normalizeProvinceCode(raw.province || suite.province),
    fullScore,
    full_score: raw.full_score ?? fullScore,
    assignedScore,
    questionMaxScore: assignedScore,
    scoringPoints: normalizeScoringPoints(raw, assignedScore),
    dimensions: Array.isArray(raw.dimensions) ? raw.dimensions : [],
    sourceDocument: getSourceDocument(raw) || suite.sourceDocument || '',
    source_document: raw.source_document || raw.sourceDocument || suite.sourceDocument || '',
    questionSourceLabel: suite.title || '',
    fullExamSuiteId: suite.id || '',
    fullExamSuiteTitle: suite.title || '',
    fullExamQuestionNumber: index + 1,
    fullExamQuestionCount: questionCount,
    fullExamAnswerScoreTotal: suite.answerScoreTotal || 0,
    fullExamAppearanceScore: suite.appearanceScore || 0,
    fullExamTotalScore: suite.totalScore || 0,
    fullExamTimingMode: raw.fullExamTimingMode || suite.timingMode || ''
  }
}

export function buildFullExamSuitesFromQuestions(questions = [], province = '') {
  const list = normalizeQuestionListResponse(questions)
  const requestedProvince = normalizeProvinceCode(province)
  const shouldFilterProvince = requestedProvince && requestedProvince !== 'national'
  const groups = new Map()

  for (const question of list) {
    const questionId = getQuestionId(question)
    const suiteKey = extractSuiteKey(questionId)
    if (!suiteKey) continue

    const questionProvince = normalizeProvinceCode(question?.province || question?.provinceCode || question?.province_code || requestedProvince)
    if (shouldFilterProvince && questionProvince !== requestedProvince) continue

    if (!groups.has(suiteKey)) {
      groups.set(suiteKey, {
        suiteKey,
        province: questionProvince,
        sourceDocument: getSourceDocument(question),
        questions: []
      })
    }

    const group = groups.get(suiteKey)
    if (!group.sourceDocument) group.sourceDocument = getSourceDocument(question)
    group.questions.push(question)
  }

  return [...groups.values()]
    .map((group) => {
      const orderedQuestions = [...group.questions].sort((a, b) => {
        const order = extractQuestionOrder(getQuestionId(a)) - extractQuestionOrder(getQuestionId(b))
        if (order !== 0) return order
        return getQuestionId(a).localeCompare(getQuestionId(b))
      })

      if (!isCompleteNumberedSuite(orderedQuestions)) return null

      const answerScoreTotal = orderedQuestions.reduce((sum, item) => sum + getQuestionScore(item), 0)
      const totalScore = Math.max(100, Math.ceil(answerScoreTotal))
      const suite = {
        id: `${group.province}-${group.suiteKey}`,
        suiteKey: group.suiteKey,
        province: group.province,
        title: buildSuiteTitle(group.province, group.suiteKey),
        sourceDocument: group.sourceDocument,
        timingMode: group.province === 'jiangsu' ? JIANGSU_FULL_EXAM_TIMING_MODE : '',
        answerScoreTotal,
        totalScore,
        appearanceScore: Math.max(0, totalScore - answerScoreTotal),
        questions: orderedQuestions,
        sortKey: buildSortKey(group.suiteKey)
      }

      return {
        ...suite,
        questions: orderedQuestions.map((question, index) => normalizeFullExamQuestion(question, suite, index))
      }
    })
    .filter(Boolean)
    .sort((a, b) => {
      const byDate = String(b.sortKey || '').localeCompare(String(a.sortKey || ''))
      if (byDate !== 0) return byDate
      return a.title.localeCompare(b.title)
    })
}

export function getFullExamSuiteSummary(suite) {
  if (!suite) return ''
  const appearanceText = suite.appearanceScore > 0 ? `，仪态 ${suite.appearanceScore} 分` : ''
  return `${suite.questions.length} 题，答题分 ${suite.answerScoreTotal} 分${appearanceText}，总分 ${suite.totalScore} 分`
}

export async function fetchFullExamSuites(getQuestions, province, options = {}) {
  if (typeof getQuestions !== 'function') return []
  const code = normalizeProvinceCode(province)
  const params = {
    current: 1,
    page: 1,
    pageSize: Number(options.pageSize || FULL_EXAM_FETCH_PAGE_SIZE)
  }
  if (code !== 'national') params.province = code

  const response = await getQuestions(params)
  return buildFullExamSuitesFromQuestions(normalizeQuestionListResponse(response), code)
}

export async function loadFullExamSuiteQuestions(suite, getQuestionById) {
  if (!suite) return []
  const loaded = []
  const questions = Array.isArray(suite.questions) ? suite.questions : []

  for (let index = 0; index < questions.length; index += 1) {
    const current = questions[index]
    const questionId = getQuestionId(current)
    const hasBody = !!getQuestionStem(current)
    const hydrated = hasBody || typeof getQuestionById !== 'function'
      ? current
      : await getQuestionById(questionId)

    if (!hydrated?.id && !questionId) {
      throw new Error(`套题题目加载失败：第 ${index + 1} 题`)
    }

    loaded.push(normalizeFullExamQuestion({
      ...current,
      ...hydrated,
      id: hydrated?.id || questionId
    }, suite, index))
  }

  return loaded
}
