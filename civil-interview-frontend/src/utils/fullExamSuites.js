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

function firstString(...values) {
  for (const value of values) {
    const text = String(value || '').trim()
    if (text) return text
  }
  return ''
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
    raw.questionScore,
    raw.question_score,
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

function getQuestionMeta(raw = {}) {
  const meta = raw?.keywords?._meta
  return meta && typeof meta === 'object' ? meta : {}
}

function getSuiteName(raw = {}) {
  const meta = getQuestionMeta(raw)
  return firstString(raw.suiteName, raw.fullExamSuiteTitle, raw.suiteTitle, meta.suiteName, meta.fullExamSuiteTitle)
}

function getSuiteKey(raw = {}) {
  const meta = getQuestionMeta(raw)
  return firstString(raw.suiteKey, raw.fullExamSuiteKey, raw.suiteId, raw.fullExamSuiteId, meta.suiteKey, meta.suiteId, extractSuiteKey(getQuestionId(raw)))
}

function getExamDate(raw = {}) {
  const meta = getQuestionMeta(raw)
  return firstString(raw.examDate, raw.exam_date, meta.examDate)
}

function getMetaString(raw = {}, ...keys) {
  const meta = getQuestionMeta(raw)
  for (const key of keys) {
    const text = firstString(raw[key], meta[key])
    if (text) return text
  }
  return ''
}

function getSuiteNumber(raw = {}, ...keys) {
  const meta = getQuestionMeta(raw)
  for (const key of keys) {
    const value = firstPositiveNumber(raw[key], meta[key])
    if (value > 0) return value
  }
  return 0
}

function hasExplicitSuiteNumber(raw = {}, ...keys) {
  const meta = getQuestionMeta(raw)
  return keys.some((key) => {
    const rawValue = raw[key]
    const metaValue = meta[key]
    return rawValue !== undefined && rawValue !== null && rawValue !== ''
      || metaValue !== undefined && metaValue !== null && metaValue !== ''
  })
}

function hasExplicitBoolean(raw = {}, ...keys) {
  const meta = getQuestionMeta(raw)
  return keys.some((key) => (
    raw[key] !== undefined && raw[key] !== null && raw[key] !== ''
  ) || (
    meta[key] !== undefined && meta[key] !== null && meta[key] !== ''
  ))
}

function getBooleanValue(raw = {}, ...keys) {
  const meta = getQuestionMeta(raw)
  for (const key of keys) {
    const value = raw[key] !== undefined ? raw[key] : meta[key]
    if (typeof value === 'boolean') return value
    if (typeof value === 'string' && value.trim()) {
      return ['1', 'true', 'yes', '有', '是'].includes(value.trim().toLowerCase())
    }
  }
  return false
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

function getQuestionOrder(raw = {}) {
  const meta = getQuestionMeta(raw)
  const explicit = firstPositiveNumber(raw.questionNo, raw.question_no, raw.fullExamQuestionNumber, meta.questionNo)
  return explicit > 0 ? explicit : extractQuestionOrder(getQuestionId(raw))
}

function isCompleteNumberedSuite(questions = []) {
  if (questions.length < MIN_SUITE_QUESTION_COUNT) return false
  const orders = questions.map((item) => getQuestionOrder(item))
  if (orders.some((order) => !Number.isFinite(order) || order === Number.MAX_SAFE_INTEGER)) return false
  const unique = new Set(orders)
  if (unique.size !== orders.length) return false
  return [...unique].sort((a, b) => a - b).every((order, index) => order === index + 1)
}

function buildSuiteTitle(province, suiteKey) {
  const provinceName = PROVINCE_CODE_TO_NAME[province] || province || '真题'
  return `${provinceName}真题套卷 ${suiteKey}`
}

function buildSortKey(suiteKey = '', examDate = '') {
  const normalizedDate = String(examDate || '').replace(/\D/g, '')
  if (/^20\d{6}$/.test(normalizedDate)) return normalizedDate
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
  const questionNumber = getQuestionOrder(raw)

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
    suiteId: raw.suiteId || suite.suiteKey || '',
    suiteKey: raw.suiteKey || suite.suiteKey || '',
    suiteName: raw.suiteName || suite.title || '',
    examDate: raw.examDate || suite.examDate || '',
    examCategory: raw.examCategory || suite.examCategory || '',
    examSubcategory: raw.examSubcategory || suite.examSubcategory || '',
    system: raw.system || suite.system || '',
    positionType: raw.positionType || suite.positionType || '',
    interviewFormat: raw.interviewFormat || suite.interviewFormat || '',
    questionTypeCategory: raw.questionTypeCategory || '',
    portalTags: Array.isArray(raw.portalTags) ? raw.portalTags : (Array.isArray(suite.portalTags) ? suite.portalTags : []),
    displayPortals: Array.isArray(raw.displayPortals) ? raw.displayPortals : (Array.isArray(suite.displayPortals) ? suite.displayPortals : []),
    classificationConfidence: raw.classificationConfidence || '',
    reviewStatus: raw.reviewStatus || '',
    reviewReason: raw.reviewReason || '',
    hasAppearanceScore: raw.hasAppearanceScore ?? suite.hasAppearanceScore ?? false,
    questionNo: questionNumber === Number.MAX_SAFE_INTEGER ? index + 1 : questionNumber,
    questionScore: assignedScore,
    fullExamQuestionNumber: questionNumber === Number.MAX_SAFE_INTEGER ? index + 1 : questionNumber,
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
    const suiteKey = getSuiteKey(question)
    if (!suiteKey) continue

    const questionProvince = normalizeProvinceCode(question?.province || question?.provinceCode || question?.province_code || requestedProvince)
    if (shouldFilterProvince && questionProvince !== requestedProvince) continue

    if (!groups.has(suiteKey)) {
      groups.set(suiteKey, {
        suiteKey,
        province: questionProvince,
        suiteName: getSuiteName(question),
        examDate: getExamDate(question),
        answerScoreTotal: getSuiteNumber(question, 'answerScoreTotal', 'fullExamAnswerScoreTotal'),
        appearanceScore: getSuiteNumber(question, 'appearanceScore', 'fullExamAppearanceScore'),
        totalScore: getSuiteNumber(question, 'suiteTotalScore', 'totalScore', 'fullExamTotalScore'),
        hasExplicitTotalScore: hasExplicitSuiteNumber(question, 'suiteTotalScore', 'totalScore', 'fullExamTotalScore'),
        hasExplicitAppearanceScore: hasExplicitSuiteNumber(question, 'appearanceScore', 'fullExamAppearanceScore'),
        hasExplicitAppearanceFlag: hasExplicitBoolean(question, 'hasAppearanceScore'),
        hasAppearanceScore: getBooleanValue(question, 'hasAppearanceScore'),
        examCategory: getMetaString(question, 'examCategory'),
        examSubcategory: getMetaString(question, 'examSubcategory'),
        system: getMetaString(question, 'system'),
        positionType: getMetaString(question, 'positionType'),
        interviewFormat: getMetaString(question, 'interviewFormat'),
        portalTags: Array.isArray(question?.portalTags) ? question.portalTags : [],
        displayPortals: Array.isArray(question?.displayPortals) ? question.displayPortals : [],
        sourceDocument: getSourceDocument(question),
        questions: []
      })
    }

    const group = groups.get(suiteKey)
    if (!group.suiteName) group.suiteName = getSuiteName(question)
    if (!group.examDate) group.examDate = getExamDate(question)
    if (!group.answerScoreTotal) group.answerScoreTotal = getSuiteNumber(question, 'answerScoreTotal', 'fullExamAnswerScoreTotal')
    if (!group.appearanceScore) group.appearanceScore = getSuiteNumber(question, 'appearanceScore', 'fullExamAppearanceScore')
    if (!group.totalScore) group.totalScore = getSuiteNumber(question, 'suiteTotalScore', 'totalScore', 'fullExamTotalScore')
    group.hasExplicitTotalScore = group.hasExplicitTotalScore || hasExplicitSuiteNumber(question, 'suiteTotalScore', 'totalScore', 'fullExamTotalScore')
    group.hasExplicitAppearanceScore = group.hasExplicitAppearanceScore || hasExplicitSuiteNumber(question, 'appearanceScore', 'fullExamAppearanceScore')
    group.hasExplicitAppearanceFlag = group.hasExplicitAppearanceFlag || hasExplicitBoolean(question, 'hasAppearanceScore')
    group.hasAppearanceScore = group.hasAppearanceScore || getBooleanValue(question, 'hasAppearanceScore')
    if (!group.examCategory) group.examCategory = getMetaString(question, 'examCategory')
    if (!group.examSubcategory) group.examSubcategory = getMetaString(question, 'examSubcategory')
    if (!group.system) group.system = getMetaString(question, 'system')
    if (!group.positionType) group.positionType = getMetaString(question, 'positionType')
    if (!group.interviewFormat) group.interviewFormat = getMetaString(question, 'interviewFormat')
    if (Array.isArray(question?.portalTags)) {
      group.portalTags = [...new Set([...group.portalTags, ...question.portalTags])]
    }
    if (Array.isArray(question?.displayPortals)) {
      group.displayPortals = [...new Set([...group.displayPortals, ...question.displayPortals])]
    }
    if (!group.sourceDocument) group.sourceDocument = getSourceDocument(question)
    group.questions.push(question)
  }

  return [...groups.values()]
    .map((group) => {
      const orderedQuestions = [...group.questions].sort((a, b) => {
        const order = getQuestionOrder(a) - getQuestionOrder(b)
        if (order !== 0) return order
        return getQuestionId(a).localeCompare(getQuestionId(b))
      })

      if (!isCompleteNumberedSuite(orderedQuestions)) return null

      const calculatedAnswerScoreTotal = orderedQuestions.reduce((sum, item) => sum + getQuestionScore(item), 0)
      const answerScoreTotal = group.answerScoreTotal || calculatedAnswerScoreTotal
      const totalScore = group.totalScore || Math.ceil(answerScoreTotal)
      const appearanceScore = group.hasExplicitAppearanceScore
        ? group.appearanceScore
        : (group.hasExplicitAppearanceFlag && !group.hasAppearanceScore)
          ? 0
          : group.hasExplicitTotalScore
          ? Math.max(0, totalScore - answerScoreTotal)
          : 0
      const hasAppearanceScore = group.hasExplicitAppearanceFlag ? group.hasAppearanceScore : appearanceScore > 0
      const suite = {
        id: `${group.province}-${group.suiteKey}`,
        suiteKey: group.suiteKey,
        province: group.province,
        title: group.suiteName || buildSuiteTitle(group.province, group.suiteKey),
        suiteName: group.suiteName || '',
        examDate: group.examDate || '',
        examCategory: group.examCategory || '',
        examSubcategory: group.examSubcategory || '',
        system: group.system || '',
        positionType: group.positionType || '',
        interviewFormat: group.interviewFormat || '',
        portalTags: group.portalTags || [],
        displayPortals: group.displayPortals || [],
        sourceDocument: group.sourceDocument,
        timingMode: group.province === 'jiangsu' ? JIANGSU_FULL_EXAM_TIMING_MODE : '',
        answerScoreTotal,
        totalScore,
        appearanceScore,
        hasAppearanceScore,
        questions: orderedQuestions,
        sortKey: buildSortKey(group.suiteKey, group.examDate)
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
  const appearanceText = suite.hasAppearanceScore ? '，含仪态评分' : '，不含仪态评分'
  return `${suite.questions.length} 题，按真实套题节奏作答${appearanceText}`
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
  const questions = Array.isArray(suite.questions) ? suite.questions : []

  const results = await Promise.allSettled(
    questions.map(async (current, index) => {
      const questionId = getQuestionId(current)
      const hasBody = !!getQuestionStem(current)
      const hydrated = hasBody || typeof getQuestionById !== 'function'
        ? current
        : await getQuestionById(questionId)

      if (!hydrated?.id && !questionId) {
        throw new Error(`套题题目加载失败：第 ${index + 1} 题`)
      }

      return normalizeFullExamQuestion({
        ...current,
        ...hydrated,
        id: hydrated?.id || questionId
      }, suite, index)
    })
  )

  const loaded = []
  for (const result of results) {
    if (result.status === 'fulfilled') {
      loaded.push(result.value)
    }
  }
  if (loaded.length !== questions.length) {
    throw new Error('套题题目加载不完整，请切换其他套卷后重试')
  }
  return loaded
}
