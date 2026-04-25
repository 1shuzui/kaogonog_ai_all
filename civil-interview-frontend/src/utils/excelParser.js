import * as XLSX from 'xlsx'

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
        const questions = Array.isArray(data) ? data : (data.questions || [])
        resolve(questions)
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
