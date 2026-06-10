/**
 * 小程序展示格式化工具把后端返回的时间、分数、日期和列表响应转成移动端稳定文案。
 *
 * 格式化层只处理可见形态，不推断业务含义；无效日期、空列表和异常分数要保守展示，避免误导订单、历史或评分结果。
 *
 * @param 无；导出函数接收原始展示值或接口响应。
 * @return 导出时间、日期、分数、文本截断和列表响应归一函数。
 * @raises 参数异常通常返回兜底值；需要阻断流程的错误交由调用方处理。
 */
export function formatTime(totalSeconds = 0) {
  const seconds = Math.max(0, Math.floor(Number(totalSeconds) || 0))
  const minute = Math.floor(seconds / 60)
  const second = seconds % 60
  return `${String(minute).padStart(2, '0')}:${String(second).padStart(2, '0')}`
}

export function formatDate(value = '') {
  if (!value) return ''
  const date = new Date(value)
  if (Number.isNaN(date.getTime())) return String(value)
  const month = String(date.getMonth() + 1).padStart(2, '0')
  const day = String(date.getDate()).padStart(2, '0')
  const hour = String(date.getHours()).padStart(2, '0')
  const minute = String(date.getMinutes()).padStart(2, '0')
  return `${date.getFullYear()}-${month}-${day} ${hour}:${minute}`
}

export function formatScore(value = 0) {
  const number = Number(value) || 0
  return Number.isInteger(number) ? String(number) : number.toFixed(1).replace(/\.0$/, '')
}

export function compactText(text = '', max = 52) {
  const source = String(text || '').replace(/\s+/g, ' ').trim()
  if (source.length <= max) return source
  return `${source.slice(0, max)}...`
}

export function normalizeListResponse(response = {}) {
  if (Array.isArray(response)) {
    return {
      list: response,
      total: response.length
    }
  }

  const list = response.list || response.data || response.items || []
  return {
    list: Array.isArray(list) ? list : [],
    total: Number(response.total ?? list.length ?? 0)
  }
}
