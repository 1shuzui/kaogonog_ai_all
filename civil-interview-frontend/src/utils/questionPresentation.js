import { DIMENSIONS, PROVINCES, getQuestionTypeName } from '@/utils/constants'
import { isQuestionScoringSupported } from '@/utils/scoringSupport'

const COMIC_QUESTION_PATTERNS = [
  /漫画/,
  /图片/,
  /图中/,
  /看图/,
  /如图/,
  /根据.*图/,
  /材料一/,
  /材料二/,
  /根据以下材料/,
  /根据下列材料/
]

const SECTION_SPLIT_PATTERNS = [
  /([一二三四五六七八九十]+\s*[、.．)）])/g,
  /(第[一二三四五六七八九十]+[问部分点题]\s*[：:、.．)?）]?)/g,
  /(\d+\s*[、.．)）])/g
]

const ORDER_LABELS = ['第一', '第二', '第三', '第四', '第五']

function normalizeArray(values = []) {
  return Array.from(
    new Set(
      (Array.isArray(values) ? values : [])
        .map((item) => String(item || '').trim())
        .filter(Boolean)
    )
  )
}

function normalizeKeywordItems(items = [], key = 'word') {
  return Array.from(
    new Set(
      (Array.isArray(items) ? items : [])
        .map((item) => String(item?.[key] || item || '').trim())
        .filter(Boolean)
    )
  )
}

export function getProvinceLabel(code = '') {
  const matched = PROVINCES.find((item) => item.code === code)
  return matched?.name || String(code || '').trim() || '未标注省份'
}

export function getDimensionLabel(key = '') {
  const matched = DIMENSIONS.find((item) => item.key === key)
  return matched?.name || String(key || '').trim() || '未分类'
}

export function isComicQuestion(text = '') {
  const content = String(text || '').trim()
  return COMIC_QUESTION_PATTERNS.some((pattern) => pattern.test(content))
}

export function isLongQuestion(text = '') {
  const content = String(text || '').trim()
  if (!content) return false
  return content.length > 120 || content.split(/\n+/).length >= 4
}

export function splitQuestionContent(text = '') {
  const raw = String(text || '').replace(/\r/g, '').trim()
  if (!raw) return []

  let normalized = raw
  SECTION_SPLIT_PATTERNS.forEach((pattern) => {
    normalized = normalized.replace(pattern, '\n$1')
  })

  return normalized
    .split(/\n+/)
    .map((item) => item.trim())
    .filter(Boolean)
}

function resolveQuestionType(question = {}) {
  const rawType = String(question?.questionType || question?.type || '').trim()
  if (rawType) return getQuestionTypeName(rawType)

  const rawDimension = String(question?.dimension || '').trim()
  if (rawDimension) return getQuestionTypeName(rawDimension)

  return '结构化面试题'
}

export function buildQuestionHighlights(question = {}, options = {}) {
  const maxKeywords = Number(options.maxKeywords || 4)
  const keywords = normalizeArray([
    ...normalizeKeywordItems(question?.keywords?.scoring),
    ...normalizeKeywordItems(question?.keywords?.bonus),
    ...normalizeArray(question?.tags)
  ]).slice(0, maxKeywords)

  const tags = [
    { key: 'type', label: resolveQuestionType(question), tone: 'type' },
    question?.province ? { key: 'province', label: getProvinceLabel(question.province), tone: 'province' } : null,
    question?.questionSourceLabel ? { key: 'source', label: question.questionSourceLabel, tone: 'source' } : null,
    !isQuestionScoringSupported(question)
      ? { key: 'scoring-unsupported', label: '未接入评分', tone: 'warning' }
      : null,
    question?.hasReferenceAnswer || question?.referenceAnswer
      ? { key: 'reference', label: '含参考要点', tone: 'reference' }
      : null
  ].filter(Boolean)

  return {
    tags,
    keywords
  }
}

function cleanPointLabel(text = '') {
  return String(text || '')
    .replace(/^[①②③④⑤⑥⑦⑧⑨⑩]/, '')
    .replace(/^第[一二三四五六七八九十]+[点部分题问]/, '')
    .replace(/^(\d+|[一二三四五六七八九十]+)[、.．:：)）\s]*/, '')
    .trim()
}

function buildPointHint(title = '') {
  const text = String(title || '')
  if (/(意义|价值|作用|影响|现象|观点|态度)/.test(text)) {
    return '先亮明立场，再补充原因、影响和岗位视角。'
  }
  if (/(原因|问题|风险|矛盾|不足)/.test(text)) {
    return '尽量说到具体表现、成因，以及不解决会带来的后果。'
  }
  if (/(措施|对策|建议|方案|组织|落实|应对|处置)/.test(text)) {
    return '把主体、步骤、落地动作和预期效果说完整。'
  }
  if (/(沟通|协调|群众|同事|领导|关系)/.test(text)) {
    return '体现对象意识、情绪安抚和协同推进。'
  }
  if (/(模拟|劝导|发言|宣传)/.test(text)) {
    return '按真实说话口吻展开，注意开场、主体和收束。'
  }
  return '补充具体场景、做法和结果，不要只停留在抽象表态。'
}

function getPointCategory(title = '') {
  const text = String(title || '')
  if (/(意义|价值|作用|影响|现象|观点|态度)/.test(text)) return 'analysis'
  if (/(原因|问题|风险|矛盾|不足)/.test(text)) return 'problem'
  if (/(措施|对策|建议|方案|组织|落实|应对|处置)/.test(text)) return 'action'
  if (/(沟通|协调|群众|同事|领导|关系)/.test(text)) return 'communication'
  if (/(模拟|劝导|发言|宣传)/.test(text)) return 'simulation'
  return 'generic'
}

function buildTeacherComment(typeLabel = '', focusPoints = []) {
  const firstPoint = focusPoints[0]?.title || ''

  if (typeLabel === '综合分析') {
    return '从批改老师的角度看，这类题最怕“只有态度，没有分析”。高分答案通常会先亮观点，再把意义、问题和对策讲成一个完整闭环。'
  }
  if (typeLabel === '组织管理') {
    return '这类题不能只说“我会认真组织”。老师更看重你能不能把前期准备、过程推进和后续复盘答成有步骤、有分工、有落点的执行方案。'
  }
  if (typeLabel === '应急应变') {
    return '应急题评分时很看重节奏感。先稳局面、再核情况、后分类处置，这个顺序如果不清楚，答案听起来就会乱。'
  }
  if (typeLabel === '人际沟通') {
    return '人际题高分不在“会沟通”这三个字，而在于你能不能把对象意识、分寸感和推动事情解决的能力说出来。'
  }
  if (typeLabel === '现场模拟') {
    return '现场模拟题最忌讳书面腔。老师更愿意给分给那些像真实交流一样自然、有称呼、有回应、有收束的表达。'
  }
  if (typeLabel === '职业认知') {
    return '职业认知类题目不能答成“个人感想”。老师重点听的是岗位理解、价值取向和你与岗位的匹配度。'
  }
  if (firstPoint) {
    return `这道题的得分重点其实比较明确，尤其是“${firstPoint}”这一层，最好答得更像考场里的完整口语作答，而不是零散表态。`
  }
  return '这道题更适合按“先判断、再展开、后收束”的方式来答，整体听感会更像结构化面试中的高分答案。'
}

function buildOpeningRewrite(typeLabel = '', focusPoints = []) {
  const categories = focusPoints.map((item) => getPointCategory(item.title))
  const hasProblem = categories.includes('problem')
  const hasAction = categories.includes('action')

  if (typeLabel === '综合分析') {
    if (hasProblem && hasAction) {
      return '这道题我认为不能简单地肯定或否定，既要看到它的现实意义，也要正视其中可能存在的问题，关键是通过完善机制把好事办好。'
    }
    return '对于这类现象和观点题，我的基本看法是要辩证分析、全面看待，既讲清价值判断，也讲清现实路径。'
  }
  if (typeLabel === '组织管理') {
    return '如果由我负责这项工作，我会坚持目标导向和结果导向，按照“前期摸底、过程推进、后续复盘”的思路有序开展。'
  }
  if (typeLabel === '应急应变') {
    return '遇到这种情况，我会把稳控局面放在第一位，在不扩大影响的前提下，迅速核实情况、分类处置、及时汇报。'
  }
  if (typeLabel === '人际沟通') {
    return '面对这种情境，我会坚持工作为先、沟通为桥，既照顾对方情绪，也推动问题得到妥善解决。'
  }
  if (typeLabel === '现场模拟') {
    return '各位，请先允许我把情况说明清楚，也请大家放心，我今天沟通的目的就是把问题解决好、把误解解释开。'
  }
  if (typeLabel === '职业认知') {
    return '报考这个岗位，我不是停留在兴趣层面，而是基于对岗位职责、服务对象和个人发展方向的综合考虑作出的选择。'
  }
  return '这道题我会先明确自己的判断，再围绕核心得分点分层展开，最后回到岗位职责和实际效果上收束。'
}

function buildClosingRewrite(typeLabel = '') {
  if (typeLabel === '综合分析') {
    return '总的来说，对这类问题既不能一味叫好，也不能简单否定，关键还是立足实际、完善机制、抓好落实。'
  }
  if (typeLabel === '组织管理') {
    return '我相信只要把前期准备做细、把过程责任压实、把后续复盘跟上，这项工作就能够取得预期效果。'
  }
  if (typeLabel === '应急应变') {
    return '我会在妥善处置当前问题的同时，及时复盘原因、堵住漏洞，避免类似情况再次发生。'
  }
  if (typeLabel === '人际沟通') {
    return '我会把这件事处理到既不影响关系，也不耽误工作，让沟通真正服务于问题解决。'
  }
  if (typeLabel === '现场模拟') {
    return '也希望大家能够理解和支持，我们一起把事情往好的方向推进。'
  }
  if (typeLabel === '职业认知') {
    return '如果有机会走上这个岗位，我也会把这种认同转化为真正服务群众、扎实履职的行动。'
  }
  return '最后，我会把答案落回到执行效果和群众感受上，让整道题有一个完整收束。'
}

function buildDiagnosisItems({
  transcript = '',
  missingKeywords = [],
  weakDimensions = [],
  focusPoints = []
} = {}) {
  const text = String(transcript || '').trim()
  const items = []
  const structureMarkers = /(第一|第二|第三|首先|其次|再次|最后|一是|二是|三是|一方面|另一方面)/
  const sentenceCount = text
    ? text.split(/[。！？!?]/).map((item) => item.trim()).filter(Boolean).length
    : 0

  if (text && text.length < 140) {
    items.push('展开偏短，像答提纲，老师会觉得你知道方向，但没有把分数真正展开。')
  }

  if (focusPoints.length >= 2 && text && !structureMarkers.test(text)) {
    items.push('分层不够明显，听感上不像标准结构化答案，建议主动用“第一、第二、第三”把层次拉开。')
  }

  if (missingKeywords.length >= 2) {
    items.push(`贴题信号还不够强，像“${missingKeywords.slice(0, 3).join('、')}”这类关键词没有自然带出来，命中率会受影响。`)
  }

  if (sentenceCount >= 1 && sentenceCount <= 3 && focusPoints.length >= 3) {
    items.push('答题骨架偏紧，几个得分点容易挤在一起，建议每个层次至少说清“观点 + 展开 + 落点”。')
  }

  weakDimensions.forEach((item) => {
    if (items.length >= 3) return
    if (item?.name === '逻辑结构') {
      items.push('逻辑主线还不够稳，段与段之间缺少过渡句，老师听到后不容易迅速抓住你的答题框架。')
      return
    }
    if (item?.name === '语言表达') {
      items.push('表达偏概括，缺少更像面试现场的完整口语句式，可以少一点泛泛表态，多一点完整判断。')
      return
    }
    if (item?.name === '实务落地') {
      items.push('措施层还可以再实一些，最好说到由谁做、怎么推、预期达到什么效果。')
      return
    }
    if (item?.name === '综合分析') {
      items.push('分析层次还不够展开，建议把“为什么、会怎样、怎么办”答成一个闭环。')
      return
    }
    if (item?.reason) {
      items.push(item.reason)
    }
  })

  return Array.from(new Set(items)).slice(0, 3)
}

function buildExpressionUpgrades(typeLabel = '', missingKeywords = []) {
  const keywordHint = missingKeywords.length
    ? `同时可自然带出“${missingKeywords.slice(0, 2).join('、')}”这样的关键词。`
    : ''

  if (typeLabel === '综合分析') {
    return [
      {
        before: '我觉得这个现象挺有意义的。',
        after: `我认为对这一现象既要看到积极意义，也要正视现实问题，关键在于通过完善机制把好事办好。${keywordHint}`
      }
    ]
  }
  if (typeLabel === '组织管理') {
    return [
      {
        before: '我会先准备一下，然后把活动办好。',
        after: `如果由我负责，我会先摸清对象需求和资源条件，再形成方案、压实分工、推进落实，最后复盘提升。${keywordHint}`
      }
    ]
  }
  if (typeLabel === '应急应变') {
    return [
      {
        before: '我会赶紧去处理这个事情。',
        after: `遇到突发情况，我会先稳控现场、核实信息、分类处置，再及时汇报并做好后续预防。${keywordHint}`
      }
    ]
  }
  if (typeLabel === '人际沟通') {
    return [
      {
        before: '我会和他好好沟通一下。',
        after: `我会先理解对方情绪和顾虑，再选择合适时机沟通解释，在维护关系的同时推动工作落地。${keywordHint}`
      }
    ]
  }
  if (typeLabel === '现场模拟') {
    return [
      {
        before: '希望大家配合一下我们的工作。',
        after: `各位的顾虑我理解，今天和大家沟通，主要是想把政策讲清楚、把问题解决好，也希望争取大家的理解和支持。${keywordHint}`
      }
    ]
  }
  if (typeLabel === '职业认知') {
    return [
      {
        before: '我报这个岗位是因为我比较喜欢。',
        after: `我报考这个岗位，不只是出于个人兴趣，更是因为认同岗位职责，愿意在服务群众和基层实践中实现个人价值。${keywordHint}`
      }
    ]
  }
  return [
    {
      before: '我会认真做好这件事。',
      after: `我会先明确判断，再围绕关键得分点分层展开，最后把答案落到执行效果和岗位职责上。${keywordHint}`
    }
  ]
}

function buildFocusRewrite(point = {}, typeLabel = '') {
  const category = getPointCategory(point.title)

  if (category === 'analysis') {
    return `${point.order}，围绕“${point.title}”这一层，不要只说“有意义”或“有影响”，最好进一步落到群众感受、治理成效、工作导向这些可得分的具体落点上。`
  }
  if (category === 'problem') {
    return `${point.order}，讲“${point.title}”时，要把问题表现、成因和后果连起来，老师会更容易判断你不是泛泛而谈。`
  }
  if (category === 'action') {
    return `${point.order}，围绕“${point.title}”，要把措施答实，最好体现“谁来做、怎么做、做到什么程度”，这样执行力才会出来。`
  }
  if (category === 'communication') {
    return `${point.order}，在“${point.title}”这一层，要体现对象意识和沟通分寸，既解决情绪，也推动事情往前走。`
  }
  if (category === 'simulation') {
    return `${point.order}，如果是现场表达，围绕“${point.title}”展开时要像真实沟通，不要读材料式输出，而要有称呼、有解释、有回应。`
  }
  if (typeLabel === '职业认知') {
    return `${point.order}，对于“${point.title}”，建议多把个人选择与岗位职责、服务对象和长期成长结合起来说，避免只谈个人兴趣。`
  }
  return `${point.order}，围绕“${point.title}”展开时，要把观点、做法和结果说完整，不要停留在一句表态上。`
}

function buildSampleAnswer({
  typeLabel = '',
  focusPoints = [],
  missingKeywords = []
} = {}) {
  const paragraphs = [buildOpeningRewrite(typeLabel, focusPoints)]

  focusPoints.forEach((point) => {
    paragraphs.push(buildFocusRewrite(point, typeLabel))
  })

  if (missingKeywords.length) {
    paragraphs.push(`在表达过程中，我还会注意自然融入“${missingKeywords.slice(0, 4).join('、')}”这些题目高频词，让答案更贴题、更像标准作答。`)
  }

  paragraphs.push(buildClosingRewrite(typeLabel))

  return paragraphs.join('\n\n')
}

export function buildImprovementReference({ question = {}, result = {}, transcript = '' } = {}) {
  const typeLabel = resolveQuestionType(question)
  const scoringPoints = Array.isArray(question?.scoringPoints) && question.scoringPoints.length
    ? question.scoringPoints
    : (Array.isArray(result?.dimensions) ? result.dimensions.map((item) => ({
        content: item?.name || '',
        score: item?.maxScore || 0
      })) : [])

  const focusPoints = scoringPoints
    .map((item, index) => ({
      order: ORDER_LABELS[index] || `第${index + 1}`,
      title: cleanPointLabel(item?.content || item?.name || ''),
      hint: buildPointHint(item?.content || item?.name || '')
    }))
    .filter((item) => item.title)
    .slice(0, 4)

  const strongKeywords = normalizeKeywordItems(result?.matchedKeywords?.scoring).slice(0, 4)
  const bonusKeywords = normalizeKeywordItems(result?.matchedKeywords?.bonus).slice(0, 3)
  const targetKeywords = normalizeArray([
    ...normalizeKeywordItems(question?.keywords?.scoring),
    ...normalizeKeywordItems(question?.keywords?.bonus)
  ])
  const missingKeywords = targetKeywords
    .filter((word) => !strongKeywords.includes(word) && !bonusKeywords.includes(word))
    .slice(0, 5)

  const weakDimensions = (Array.isArray(result?.dimensions) ? result.dimensions : [])
    .filter((item) => Number(item?.maxScore || 0) > 0)
    .filter((item) => (Number(item?.score || 0) / Number(item?.maxScore || 1)) < 0.75)
    .slice(0, 3)
    .map((item) => ({
      name: item.name,
      reason: Array.isArray(item?.lostReasons) && item.lostReasons.length
        ? item.lostReasons[0]
        : '这一维度还需要补充更具体的内容。'
    }))

  const diagnosisItems = buildDiagnosisItems({
    transcript,
    missingKeywords,
    weakDimensions,
    focusPoints
  })
  const teacherComment = buildTeacherComment(typeLabel, focusPoints)
  const rewriteOpening = buildOpeningRewrite(typeLabel, focusPoints)
  const rewriteClosing = buildClosingRewrite(typeLabel)
  const expressionUpgrades = buildExpressionUpgrades(typeLabel, missingKeywords)
  const sampleAnswer = buildSampleAnswer({
    typeLabel,
    focusPoints,
    missingKeywords
  })

  const summary = strongKeywords.length
    ? `这道题你不是完全没答到点上，像${strongKeywords.join('、')}这些有效内容已经提到了；但从批改视角看，答案还不够像“标准高分作答”，主要差在结构展开和表达完成度上。`
    : '这道题目前更像“想到什么说什么”，还没有形成老师愿意给高分的完整答题形态，建议先把框架和展开层次补齐。'

  return {
    available: Boolean(focusPoints.length || weakDimensions.length || missingKeywords.length),
    basis: question?.hasReferenceAnswer || question?.referenceAnswer
      ? '已结合题目采分点、关键词、可访问题库信息和本次评分结果整理。'
      : '已结合题目采分点、关键词和本次评分结果整理。',
    typeLabel,
    summary,
    teacherComment,
    diagnosisItems,
    strongKeywords,
    bonusKeywords,
    missingKeywords,
    weakDimensions,
    focusPoints,
    rewriteOpening,
    rewriteClosing,
    expressionUpgrades,
    sampleAnswer
  }
}
