const filterFields = ['province', 'year', 'examCategory', 'examSubcategory', 'subcategory', 'subcategory2', 'dimension', 'position', 'portal', 'keyword', 'categoryReview']
const scalar = value => String(Array.isArray(value) ? value[0] || '' : value || '').trim()

export function readPracticeSelection(query = {}, cachedQuestions = []) {
  const single = scalar(query.questionId)
  const raw = scalar(query.questionIds)
  let ids = single ? [single] : raw ? raw.split(',') : cachedQuestions.map(item => item.id)
  ids = ids.map(id => scalar(id))
  if (ids.length > 10 || ids.some(id => !id || id.length > 128) || new Set(ids).size !== ids.length) {
    throw new Error('所选题目列表不完整，请返回选题页重新确认')
  }
  let snapshot = query
  if (query.filterSnapshot) {
    const value = scalar(query.filterSnapshot)
    try { snapshot = JSON.parse(value) }
    catch {
      try { snapshot = JSON.parse(decodeURIComponent(value)) }
      catch { throw new Error('筛选条件读取失败，请返回题库重试') }
    }
    if (!snapshot || Array.isArray(snapshot) || typeof snapshot !== 'object') throw new Error('筛选条件读取失败，请返回题库重试')
  }
  const filters = Object.fromEntries(filterFields.filter(key => snapshot[key] != null).map(key => [key, scalar(snapshot[key])]))
  return { ids, filters }
}

export async function loadSelectedQuestions(ids, fetchQuestion) {
  // Promise.all preserves the selected order; no partial set or random replacement is valid.
  const questions = await Promise.all(ids.map(async id => {
    const question = await fetchQuestion(id)
    if (!question || String(question.id) !== id) throw new Error('指定题目暂时无法读取，已保留选择，请重试')
    return question
  }))
  return questions
}

export function practiceModeFor(source, mode = 'free', trial = false) {
  if (trial) return 'trial'
  if (mode === 'fullExam') return 'fullExam'
  return ['targeted', 'training'].includes(source) ? source : 'free'
}

export function practiceQuery({ source = 'bank', questionId = '', questionIds = [], filters = {} } = {}) {
  return {
    source,
    ...(questionId ? { questionId } : questionIds.length ? { questionIds: questionIds.join(',') } : {}),
    filterSnapshot: JSON.stringify(Object.fromEntries(filterFields.filter(key => filters[key] != null).map(key => [key, scalar(filters[key])]))),
  }
}

export function miniPracticeUrl(options) {
  const query = practiceQuery(options)
  return `/pages/exam/prepare?${Object.entries(query).map(([key, value]) => `${key}=${encodeURIComponent(value)}`).join('&')}`
}

export function practiceFilterSummary(filters, provinces = [], dimensions = []) {
  const province = provinces.find(item => item.code === filters.province)?.name || filters.province
  const dimension = dimensions.find(item => item.key === filters.dimension)?.name || filters.dimension
  return [filters.examCategory, province, filters.year ? `${filters.year.split(',').join('、')} 年` : '', filters.examSubcategory, filters.subcategory, filters.subcategory2, dimension, filters.position].filter(Boolean).join(' · ')
}
