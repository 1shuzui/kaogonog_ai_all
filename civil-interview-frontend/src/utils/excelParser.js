import * as XLSX from 'xlsx'

const PROVINCE_MAP = {
  national: 'national',
  国家: 'national',
  国考: 'national',
  国家公务员考试: 'national',
  beijing: 'beijing',
  北京: 'beijing',
  guangdong: 'guangdong',
  广东: 'guangdong',
  zhejiang: 'zhejiang',
  浙江: 'zhejiang',
  sichuan: 'sichuan',
  四川: 'sichuan',
  jiangsu: 'jiangsu',
  江苏: 'jiangsu',
  henan: 'henan',
  河南: 'henan',
  shandong: 'shandong',
  山东: 'shandong',
  hubei: 'hubei',
  湖北: 'hubei',
  hunan: 'hunan',
  湖南: 'hunan',
  liaoning: 'liaoning',
  辽宁: 'liaoning',
  shanxi: 'shanxi',
  陕西: 'shanxi'
}

/**
 * 解析Excel文件为题库数据
 * @param {File} file Excel文件
 * @returns {Promise<Array>} 解析后的题目数组
 */
export async function parseExcelFile(file) {
  return new Promise((resolve, reject) => {
    const reader = new FileReader()
    reader.onload = (e) => {
      try {
        const workbook = XLSX.read(e.target.result, { type: 'array' })
        const sheetName = workbook.SheetNames[0]
        const worksheet = workbook.Sheets[sheetName]
        const rawData = XLSX.utils.sheet_to_json(worksheet)

        const questions = rawData.map((row, index) => ({
          id: `import_${Date.now()}_${index}`,
          stem: row['题干'] || row['stem'] || '',
          dimension: row['所属维度'] || row['dimension'] || '',
          province: row['省份'] || row['province'] || 'national',
          prepTime: Number(row['准备时间'] || row['prepTime']) || 90,
          answerTime: Number(row['作答时间'] || row['answerTime']) || 180,
          scoringPoints: parseJsonField(row['采分点'] || row['scoringPoints'], []),
          sourceDocument: row['来源文档'] || row['sourceDocument'] || '',
          referenceAnswer: row['参考答案'] || row['referenceAnswer'] || '',
          scoreBands: parseJsonField(row['分段标准'] || row['scoreBands'], []),
          regressionCases: parseJsonField(row['回归样例'] || row['regressionCases'], []),
          tags: parseJsonField(row['标签'] || row['tags'], []),
          coreKeywords: parseJsonField(row['核心关键词'] || row['coreKeywords'], []),
          strongKeywords: parseJsonField(row['强关联关键词'] || row['strongKeywords'], []),
          weakKeywords: parseJsonField(row['弱关联关键词'] || row['weakKeywords'], []),
          bonusKeywords: parseJsonField(row['加分关键词'] || row['bonusKeywords'], []),
          penaltyKeywords: parseJsonField(row['惩罚关键词'] || row['penaltyKeywords'], []),
          synonyms: parseJsonField(row['同义表述库'] || row['synonyms'], []),
          keywords: {
            scoring: parseJsonField(row['得分关键词'] || row['scoringKeywords'], []),
            deducting: parseJsonField(row['扣分关键词'] || row['deductingKeywords'], []),
            bonus: parseJsonField(row['加分关键词'] || row['bonusKeywords'], [])
          }
        }))

        resolve(questions)
      } catch (err) {
        reject(new Error('Excel解析失败: ' + err.message))
      }
    }
    reader.onerror = () => reject(new Error('文件读取失败'))
    reader.readAsArrayBuffer(file)
  })
}

/**
 * 解析JSON文件为题库数据
 */
export async function parseJsonFile(file) {
  return new Promise((resolve, reject) => {
    const reader = new FileReader()
    reader.onload = (e) => {
      try {
        const data = JSON.parse(e.target.result)
        resolve(normalizeJsonPayload(data))
      } catch (err) {
        reject(new Error('JSON解析失败: ' + err.message))
      }
    }
    reader.onerror = () => reject(new Error('文件读取失败'))
    reader.readAsText(file)
  })
}

function parseJsonField(value, fallback) {
  if (!value) return fallback
  if (Array.isArray(value)) return value
  if (typeof value === 'string') {
    try {
      const parsed = JSON.parse(value)
      return Array.isArray(parsed) ? parsed : fallback
    } catch {
      // 尝试按逗号分隔
      return value.split(/[,，]/).map(s => s.trim()).filter(Boolean)
    }
  }
  return fallback
}

function normalizeJsonPayload(data) {
  if (Array.isArray(data)) {
    return data.map(normalizeQuestionItem).filter(Boolean)
  }
  if (Array.isArray(data?.questions)) {
    return data.questions.map(normalizeQuestionItem).filter(Boolean)
  }
  if (data && typeof data === 'object') {
    const item = normalizeQuestionItem(data)
    return item ? [item] : []
  }
  return []
}

function normalizeQuestionItem(item) {
  if (!item || typeof item !== 'object') return null

  const stem = String(
    item.stem ||
    item.question ||
    item.questionText ||
    item.content ||
    item.title ||
    ''
  ).trim()
  if (!stem) return null

  return {
    id: item.id || `import_${Date.now()}_${Math.random().toString(36).slice(2, 8)}`,
    stem,
    dimension: normalizeDimension(item.dimension, item.type, stem),
    province: normalizeProvince(item.province),
    prepTime: Number(item.prepTime) || 90,
    answerTime: Number(item.answerTime) || 180,
    scoringPoints: normalizeScoringPoints(item),
    sourceDocument: String(item.sourceDocument || '').trim(),
    referenceAnswer: String(item.referenceAnswer || '').trim(),
    scoreBands: parseJsonField(item.scoreBands, []),
    regressionCases: parseJsonField(item.regressionCases, []),
    tags: parseJsonField(item.tags, []),
    coreKeywords: parseJsonField(item.coreKeywords, []),
    strongKeywords: parseJsonField(item.strongKeywords, []),
    weakKeywords: parseJsonField(item.weakKeywords, []),
    bonusKeywords: parseJsonField(item.bonusKeywords, []),
    penaltyKeywords: parseJsonField(item.penaltyKeywords, []),
    synonyms: parseJsonField(item.synonyms, []),
    keywords: normalizeKeywords(item)
  }
}

function normalizeProvince(value) {
  const raw = String(value || '').trim()
  if (!raw) return 'national'
  return PROVINCE_MAP[raw] || PROVINCE_MAP[raw.toLowerCase()] || 'national'
}

function normalizeDimension(rawDimension, rawType, stem) {
  const raw = String(rawDimension || '').trim()
  if (['analysis', 'practical', 'emergency', 'legal', 'logic', 'expression'].includes(raw)) {
    return raw
  }

  const text = `${raw} ${rawType || ''} ${stem || ''}`
  if (/(应急|突发|危机|舆情)/.test(text)) return 'emergency'
  if (/(法治|法律|执法|依法)/.test(text)) return 'legal'
  if (/(表达|演讲|发言|口才)/.test(text)) return 'expression'
  if (/(逻辑|论证|结构)/.test(text)) return 'logic'
  if (/(组织|策划|沟通|协调|宣传|调研|接待|群众工作|人际)/.test(text)) return 'practical'
  return 'analysis'
}

function normalizeScoringPoints(item) {
  if (Array.isArray(item.scoringPoints) && item.scoringPoints.length) {
    return item.scoringPoints.map(point => {
      if (typeof point === 'string') return { content: point, score: 5 }
      return {
        content: point.content || point.name || '',
        score: Number(point.score) || 5
      }
    }).filter(point => point.content)
  }

  if (Array.isArray(item.dimensions) && item.dimensions.length) {
    return item.dimensions
      .map(point => ({
        content: point?.name || '',
        score: Number(point?.score) || 5
      }))
      .filter(point => point.content)
  }

  if (Array.isArray(item.scoringCriteria) && item.scoringCriteria.length) {
    return item.scoringCriteria
      .map(text => String(text || '').trim())
      .filter(Boolean)
      .map(text => ({ content: text.slice(0, 120), score: 5 }))
  }

  return []
}

function normalizeKeywords(item) {
  if (item.keywords && typeof item.keywords === 'object') {
    return {
      scoring: parseJsonField(item.keywords.scoring, []),
      deducting: parseJsonField(item.keywords.deducting || item.keywords.penalty, []),
      bonus: parseJsonField(item.keywords.bonus, [])
    }
  }

  return {
    scoring: uniq([
      ...parseJsonField(item.scoringKeywords, []),
      ...parseJsonField(item.coreKeywords, []),
      ...parseJsonField(item.strongKeywords, []),
      ...parseJsonField(item.weakKeywords, [])
    ]),
    deducting: uniq([
      ...parseJsonField(item.deductingKeywords, []),
      ...parseJsonField(item.penaltyKeywords, [])
    ]),
    bonus: uniq(parseJsonField(item.bonusKeywords, []))
  }
}

function uniq(items) {
  return [...new Set((items || []).map(item => String(item).trim()).filter(Boolean))]
}
