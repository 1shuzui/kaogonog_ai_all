export function resolveMediaUrl(value, apiBase = '/api') {
  const url = String(value || '').trim()
  if (!url || /^(https?:|blob:|wxfile:|file:)/i.test(url)) return url
  const base = String(apiBase || '/api').replace(/\/+$/, '')
  if (/^\/?uploads\//.test(url)) return `${base}/${url.replace(/^\//, '')}`
  if (url.startsWith('/')) {
    const origin = base.match(/^https?:\/\/[^/]+/i)?.[0] || ''
    return `${origin}${url}`
  }
  return `${base}/${url}`
}

export function resolveAnswerMedia(answer = {}, result = null, apiBase = '/api') {
  const record = result?.mediaRecord || answer.scoringResult?.mediaRecord || {}
  const url = answer.mediaUrl || record.fileUrl || answer.filePath || ''
  const type = String(answer.mediaMimeType || record.mediaType || answer.mediaType || answer.recordingBlob?.type || '').toLowerCase()
  const kind = type.includes('video') ? 'video' : type.includes('audio') ? 'audio' : /\.(mp4|mov|m4v|webm)(\?|$)/i.test(url) ? 'video' : 'audio'
  return { url: resolveMediaUrl(url, apiBase), kind, persisted: !!(answer.mediaUrl || record.fileUrl) }
}
