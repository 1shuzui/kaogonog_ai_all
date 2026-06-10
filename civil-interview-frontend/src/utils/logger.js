/**
 * PC 日志工具统一控制输出级别并脱敏 token、openid、支付签名等敏感字段。
 *
 * 支付、登录和录音链路排查需要上下文，但不能把用户凭证或微信虚拟支付参数打进浏览器控制台；生产环境默认只保留错误级别。
 *
 * @param 无；导出函数接收日志级别、消息和结构化 metadata。
 * @return 导出脱敏、requestId 生成和分级日志方法，供 API 层、store 和页面复用。
 * @raises 参数异常通常返回兜底值；需要阻断流程的错误交由调用方处理。
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
  if (typeof crypto !== 'undefined' && typeof crypto.randomUUID === 'function') {
    return crypto.randomUUID()
  }
  return `${Date.now().toString(36)}-${Math.random().toString(36).slice(2, 10)}`
}

function write(level, message, metadata = {}) {
  const currentLevel = resolveLevel()
  if (LEVELS[level] < LEVELS[currentLevel] || currentLevel === 'silent') return
  if (typeof console === 'undefined') return

  const entry = redact({
    timestamp: new Date().toISOString(),
    level,
    app: 'civil-interview-frontend',
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
