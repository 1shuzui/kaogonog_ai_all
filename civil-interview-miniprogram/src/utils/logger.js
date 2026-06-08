/**
 * 这个工具文件处理 `logger` 这类跨页面规则；集中维护可以避免 PC、小程序或不同页面各自写一份判断。
 *
 * @param 无；文件级模块依赖导出函数、组合式 API 或调用方传入上下文。
 * @return 导出可复用的端侧能力，具体返回值由各公共函数保持兼容。
 * @raises 不主动吞掉业务异常；请求失败、权限不足和运行时错误交由调用方或全局拦截器处理。
 */
const LEVELS = {
  debug: 10,
  info: 20,
  warn: 30,
  error: 40,
  silent: 99
}

const SENSITIVE_KEYS = [
  'authorization',
  'token',
  'password',
  'secret',
  'api_key',
  'apikey',
  'private_key',
  'signature',
  'pay_sign',
  'paysign',
  'openid',
  'open_id',
  'session_key',
  'access_token',
  'refresh_token'
]

const SENSITIVE_PATTERNS = [
  /(Bearer\s+)[A-Za-z0-9._~+/=-]+/gi,
  /([?&](?:token|access_token|secret|password|key)=)[^&\s]+/gi,
  /((?:api[_-]?key|secret|password|token)\s*[:=]\s*)[^\s,;}]+/gi
]

function resolveLevel() {
  const configured = String(import.meta.env.VITE_LOG_LEVEL || '').trim().toLowerCase()
  if (Object.prototype.hasOwnProperty.call(LEVELS, configured)) {
    return configured
  }
  return import.meta.env.PROD ? 'error' : 'debug'
}

function isSensitiveKey(key) {
  const normalized = String(key || '').toLowerCase().replace(/-/g, '_')
  return SENSITIVE_KEYS.some((item) => normalized.includes(item))
}

function redactString(value) {
  return SENSITIVE_PATTERNS.reduce(
    (current, pattern) => current.replace(pattern, '$1***'),
    String(value)
  )
}

export function redact(value, seen = new WeakSet()) {
  if (value == null || ['boolean', 'number', 'bigint'].includes(typeof value)) return value
  if (typeof value === 'string') return redactString(value)
  if (value instanceof Error) {
    return {
      name: value.name,
      message: redactString(value.message || ''),
      stack: value.stack ? redactString(value.stack) : ''
    }
  }
  if (Array.isArray(value)) {
    return value.map((item) => redact(item, seen))
  }
  if (typeof value === 'object') {
    if (seen.has(value)) return '[Circular]'
    seen.add(value)
    return Object.entries(value).reduce((payload, [key, item]) => {
      payload[key] = isSensitiveKey(key) ? '***' : redact(item, seen)
      return payload
    }, {})
  }
  return redactString(value)
}

export function createRequestId() {
  return `${Date.now().toString(36)}-${Math.random().toString(36).slice(2, 10)}`
}

function write(level, message, metadata = {}) {
  const currentLevel = resolveLevel()
  if (LEVELS[level] < LEVELS[currentLevel] || currentLevel === 'silent') return
  if (typeof console === 'undefined') return

  const entry = redact({
    timestamp: new Date().toISOString(),
    level,
    app: 'civil-interview-miniprogram',
    message,
    ...metadata
  })
  const method = level === 'debug' ? 'debug' : level
  const writer = console[method] || console['log']
  writer.call(console, entry)
}

export const logger = {
  debug: (message, metadata) => write('debug', message, metadata),
  info: (message, metadata) => write('info', message, metadata),
  warn: (message, metadata) => write('warn', message, metadata),
  error: (message, metadata) => write('error', message, metadata)
}
