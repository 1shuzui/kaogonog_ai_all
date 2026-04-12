/**
 * 语音分析 composable
 * 纯前端分析转写文本，计算语速、口头禅、流畅度等指标
 */

// 常见口头禅/语气词
const FILLER_WORDS = [
  '嗯', '啊', '呃', '那个', '就是说', '然后', '就是',
  '这个', '那么', '反正', '其实', '所以说', '怎么说呢',
  '额', '哦', '吧', '嘛', '呢', '啦', '哈'
]

// 政务规范用语（加分项）
const FORMAL_PHRASES = [
  '我认为', '综合来看', '首先', '其次', '最后', '总的来说',
  '具体而言', '一方面', '另一方面', '从以下几个方面',
  '第一', '第二', '第三', '因此', '综上所述',
  '结合实际', '切实', '统筹兼顾', '以人民为中心'
]

/**
 * 分析转写文本的语音表达质量
 * @param {string} transcript - 转写文本
 * @param {number} durationSeconds - 录音时长（秒）
 * @returns {object} 分析结果
 */
export function analyzeSpeech(transcript, durationSeconds) {
  if (!transcript || !durationSeconds) {
    return {
      speechRate: 0,
      speechRateLevel: '无数据',
      fillerCount: 0,
      fillerDetails: [],
      formalPhrases: [],
      fluencyScore: 0,
      fluencyLevel: '无数据',
      suggestions: ['暂无足够的语音数据进行分析']
    }
  }

  // 1. 计算语速（字/分钟）
  const charCount = transcript.replace(/\s/g, '').length
  const minutes = durationSeconds / 60
  const speechRate = Math.round(charCount / minutes)

  let speechRateLevel
  if (speechRate < 160) {
    speechRateLevel = '偏慢'
  } else if (speechRate <= 240) {
    speechRateLevel = '适中'
  } else {
    speechRateLevel = '偏快'
  }

  // 2. 口头禅检测
  const fillerDetails = []
  let fillerCount = 0
  for (const filler of FILLER_WORDS) {
    const regex = new RegExp(filler, 'g')
    const matches = transcript.match(regex)
    if (matches && matches.length > 0) {
      fillerCount += matches.length
      fillerDetails.push({ word: filler, count: matches.length })
    }
  }
  // 按出现次数降序
  fillerDetails.sort((a, b) => b.count - a.count)

  // 3. 规范用语检测
  const formalPhrases = []
  for (const phrase of FORMAL_PHRASES) {
    if (transcript.includes(phrase)) {
      formalPhrases.push(phrase)
    }
  }

  // 4. 流畅度评分（0-100）
  // 基于：语速是否适中、口头禅频率、规范用语使用
  let fluencyScore = 60 // 基础分

  // 语速评分（±15分）
  if (speechRate >= 160 && speechRate <= 240) {
    fluencyScore += 15
  } else if (speechRate >= 130 && speechRate <= 280) {
    fluencyScore += 5
  } else {
    fluencyScore -= 10
  }

  // 口头禅惩罚（每次-2分，最多-20分）
  const fillerPenalty = Math.min(fillerCount * 2, 20)
  fluencyScore -= fillerPenalty

  // 规范用语加分（每个+3分，最多+15分）
  const formalBonus = Math.min(formalPhrases.length * 3, 15)
  fluencyScore += formalBonus

  // 内容充实度（字数/时间比）
  if (charCount > 100 && minutes > 0.5) {
    fluencyScore += 10
  }

  fluencyScore = Math.max(0, Math.min(100, fluencyScore))

  let fluencyLevel
  if (fluencyScore >= 80) {
    fluencyLevel = '流畅'
  } else if (fluencyScore >= 60) {
    fluencyLevel = '一般'
  } else {
    fluencyLevel = '需改进'
  }

  // 5. 生成建议
  const suggestions = []
  if (speechRateLevel === '偏快') {
    suggestions.push('语速偏快，建议放慢节奏，适当增加停顿，让考官更好地理解你的观点')
  } else if (speechRateLevel === '偏慢') {
    suggestions.push('语速偏慢，建议加快节奏，确保在规定时间内完整表达观点')
  }

  if (fillerCount > 3) {
    const topFillers = fillerDetails.slice(0, 3).map(f => `"${f.word}"`).join('、')
    suggestions.push(`口头禅较多（${topFillers}），建议用短暂停顿替代语气词，增强表达的专业性`)
  }

  if (formalPhrases.length < 2) {
    suggestions.push('建议多使用"首先/其次/最后"、"综合来看"等结构化表达，提升语言规范性')
  }

  if (suggestions.length === 0) {
    suggestions.push('语言表达整体流畅，继续保持！可适当增加案例引用和数据支撑')
  }

  return {
    speechRate,
    speechRateLevel,
    fillerCount,
    fillerDetails,
    formalPhrases,
    fluencyScore,
    fluencyLevel,
    suggestions
  }
}
