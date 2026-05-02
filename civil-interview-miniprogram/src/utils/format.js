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
