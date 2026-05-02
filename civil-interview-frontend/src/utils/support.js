export const SUPPORT_CONTACT = {
  adminName: '平台管理员',
  wechatId: '请替换为你的客服微信号',
  workTime: '09:00 - 21:00',
  serviceScope: '题目内容反馈、题库版本差异、支付权益异常、录音评分报错'
}

export const FEEDBACK_TYPES = [
  '题库内容问题',
  '题目标签/分类问题',
  '支付或权益问题',
  '录音/视频异常',
  '评分结果疑问',
  '页面显示问题',
  '其他建议'
]

export const FEEDBACK_STATUS_OPTIONS = [
  { value: 'pending', label: '待处理' },
  { value: 'handled', label: '已处理' }
]

const STORAGE_KEY = 'civil_support_feedback_records'

function normalizeFeedbackRecord(record = {}) {
  return {
    id: record.id || `feedback_${Date.now()}_${Math.random().toString(36).slice(2, 8)}`,
    createdAt: record.createdAt || new Date().toISOString(),
    status: record.status || 'pending',
    handledAt: record.handledAt || '',
    ...record
  }
}

export function loadFeedbackRecords() {
  try {
    const raw = localStorage.getItem(STORAGE_KEY)
    const parsed = raw ? JSON.parse(raw) : []
    return Array.isArray(parsed) ? parsed.map((item) => normalizeFeedbackRecord(item)) : []
  } catch {
    return []
  }
}

export function saveFeedbackRecord(record) {
  const current = loadFeedbackRecords()
  const nextRecord = normalizeFeedbackRecord({
    ...record,
    status: 'pending',
    handledAt: ''
  })
  const next = [nextRecord, ...current].slice(0, 200)
  localStorage.setItem(STORAGE_KEY, JSON.stringify(next))
  return nextRecord
}

export function updateFeedbackRecord(recordId, patch = {}) {
  const current = loadFeedbackRecords()
  const next = current.map((item) => {
    if (item.id !== recordId) return item
    const status = patch.status || item.status
    return normalizeFeedbackRecord({
      ...item,
      ...patch,
      status,
      handledAt: status === 'handled'
        ? (patch.handledAt || item.handledAt || new Date().toISOString())
        : ''
    })
  })
  localStorage.setItem(STORAGE_KEY, JSON.stringify(next))
  return next
}

export function removeFeedbackRecord(recordId) {
  const current = loadFeedbackRecords()
  const next = current.filter((item) => item.id !== recordId)
  localStorage.setItem(STORAGE_KEY, JSON.stringify(next))
  return next
}
