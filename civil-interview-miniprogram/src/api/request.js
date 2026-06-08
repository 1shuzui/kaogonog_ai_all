/**
 * 这个文件是小程序所有后端请求的入口；401、token 和错误提示都在这里统一处理，避免页面各自弹登录。
 *
 * @param 无；文件级模块依赖导出函数、组合式 API 或调用方传入上下文。
 * @return 导出可复用的端侧能力，具体返回值由各公共函数保持兼容。
 * @raises 不主动吞掉业务异常；请求失败、权限不足和运行时错误交由调用方或全局拦截器处理。
 */
import { TOKEN_STORAGE_KEY, USERNAME_STORAGE_KEY } from '../utils/constants'
import { createRequestId, logger } from '../utils/logger'
import { toast } from '../utils/navigation'

const RUNTIME_API_BASE_KEY = 'civil_runtime_api_base'
const DEFAULT_API_BASE = 'https://xzqianmianyuzhoukeji.com/api'

function normalizeBase(base) {
  return String(base || '').trim().replace(/\/+$/, '')
}

function readRuntimeApiBase() {
  try {
    return normalizeBase(uni.getStorageSync(RUNTIME_API_BASE_KEY))
  } catch {
    return ''
  }
}

function clearRuntimeApiBase() {
  try {
    uni.removeStorageSync(RUNTIME_API_BASE_KEY)
  } catch {
    // Storage can be unavailable during very early app bootstrap in devtools.
  }
}

function isLegacyOrUnsafeApiBase(base) {
  const normalized = normalizeBase(base)
  return (
    !normalized
    || normalized === '/api'
    || normalized.startsWith('/')
    || normalized.includes('xzqianmianyuzhoukeji.cn')
    || /localhost|127\.0\.0\.1|0\.0\.0\.0/i.test(normalized)
  )
}

function resolveRuntimeApiBase(fallbackBase) {
  const runtimeBase = readRuntimeApiBase()
  if (!runtimeBase) return ''

  if (import.meta.env.PROD || isLegacyOrUnsafeApiBase(runtimeBase)) {
    clearRuntimeApiBase()
    return ''
  }

  if (!/^https?:\/\//i.test(runtimeBase)) {
    clearRuntimeApiBase()
    return ''
  }

  return runtimeBase || fallbackBase
}

function resolveApiBase() {
  const h5Base = normalizeBase(import.meta.env.VITE_API_BASE_H5)
  const mpWeixinBase = normalizeBase(import.meta.env.VITE_API_BASE_MP_WEIXIN)
  const commonBase = normalizeBase(import.meta.env.VITE_API_BASE)

  // #ifdef MP-WEIXIN
  {
    const fallbackBase = mpWeixinBase || commonBase || DEFAULT_API_BASE
    return resolveRuntimeApiBase(fallbackBase) || fallbackBase
  }
  // #endif
  // #ifdef H5
  {
    const fallbackBase = h5Base || commonBase || DEFAULT_API_BASE
    return resolveRuntimeApiBase(fallbackBase) || fallbackBase
  }
  // #endif
  {
    const fallbackBase = mpWeixinBase || h5Base || commonBase || DEFAULT_API_BASE
    return resolveRuntimeApiBase(fallbackBase) || fallbackBase
  }
}

export const API_BASE = resolveApiBase()
let unauthorizedRedirecting = false

function nowMs() {
  return Date.now()
}

function joinUrl(path = '') {
  const value = String(path || '')
  if (/^https?:\/\//.test(value)) return value
  if (!API_BASE) return value
  return `${API_BASE}${value.startsWith('/') ? value : `/${value}`}`
}

function getAuthHeader() {
  const token = uni.getStorageSync(TOKEN_STORAGE_KEY)
  return token ? { Authorization: `Bearer ${token}` } : {}
}

function normalizeErrorMessage(payload, fallback = '请求失败') {
  const detail = payload?.detail ?? payload?.message ?? payload
  if (Array.isArray(detail)) {
    return detail
      .map((item) => item?.msg || item?.message || item)
      .filter(Boolean)
      .join('; ') || fallback
  }
  if (detail && typeof detail === 'object') {
    return detail.msg || detail.message || fallback
  }
  return detail ? String(detail) : fallback
}

function handleUnauthorized() {
  uni.removeStorageSync(TOKEN_STORAGE_KEY)
  uni.removeStorageSync(USERNAME_STORAGE_KEY)
  if (unauthorizedRedirecting) return
  unauthorizedRedirecting = true
  toast('登录已过期，请重新登录')
  setTimeout(() => {
    uni.reLaunch({
      url: '/pages/login/index',
      complete: () => {
        unauthorizedRedirecting = false
      }
    })
  }, 0)
}

function normalizeNetworkError(err) {
  const rawMessage = String(err?.errMsg || err?.message || '')
  if (
    rawMessage.includes('ERR_CONNECTION_REFUSED')
    || rawMessage.includes('request:fail')
    || rawMessage.includes('timeout')
  ) {
    return `后端服务连接失败：${API_BASE || '(未配置 API 地址)'}。请检查 VITE_API_BASE_MP_WEIXIN / VITE_API_BASE_H5 配置，或清理微信开发者工具缓存后重新导入小程序。`
  }
  return rawMessage || '网络请求失败，请检查后端服务'
}

function getCurrentUserId() {
  return uni.getStorageSync(USERNAME_STORAGE_KEY) || ''
}

function logRequestStarted({ requestId, method, url, upload = false }) {
  logger.debug(upload ? 'API upload started' : 'API request started', {
    event: upload ? 'api.upload.started' : 'api.request.started',
    request_id: requestId,
    user_id: getCurrentUserId(),
    method,
    url
  })
}

function logRequestCompleted({ requestId, method, url, statusCode, durationMs, upload = false }) {
  logger.debug(upload ? 'API upload completed' : 'API request completed', {
    event: upload ? 'api.upload.completed' : 'api.request.completed',
    request_id: requestId,
    user_id: getCurrentUserId(),
    method,
    url,
    status_code: statusCode,
    duration_ms: durationMs
  })
}

function logRequestFailed({ requestId, method, url, statusCode = 0, durationMs, error, upload = false }) {
  const write = statusCode >= 500 || statusCode === 0 ? logger.error : logger.warn
  write(upload ? 'API upload failed' : 'API request failed', {
    event: upload ? 'api.upload.failed' : 'api.request.failed',
    request_id: requestId,
    user_id: getCurrentUserId(),
    method,
    url,
    status_code: statusCode,
    duration_ms: durationMs,
    error
  })
}

export function request(options = {}) {
  const {
    url,
    method = 'GET',
    data = {},
    header = {},
    timeout = 30000,
    skipErrorHandler = false
  } = options
  const requestId = header['X-Request-ID'] || header['x-request-id'] || createRequestId()
  const requestUrl = joinUrl(url)
  const requestMethod = String(method || 'GET').toUpperCase()
  const startedAt = nowMs()
  logRequestStarted({ requestId, method: requestMethod, url: requestUrl })

  return new Promise((resolve, reject) => {
    uni.request({
      url: requestUrl,
      method,
      data,
      timeout,
      header: {
        ...getAuthHeader(),
        'X-Request-ID': requestId,
        ...header
      },
      success(res) {
        const status = Number(res.statusCode || 0)
        const durationMs = nowMs() - startedAt
        if (status >= 200 && status < 300) {
          logRequestCompleted({
            requestId,
            method: requestMethod,
            url: requestUrl,
            statusCode: status,
            durationMs
          })
          resolve(res.data)
          return
        }

        const message = normalizeErrorMessage(res.data, status >= 500 ? '服务暂时不可用' : '请求失败')
        const error = new Error(message)
        error.statusCode = status
        error.data = res.data
        logRequestFailed({
          requestId,
          method: requestMethod,
          url: requestUrl,
          statusCode: status,
          durationMs,
          error
        })

        if (status === 401) {
          handleUnauthorized()
        } else if (!skipErrorHandler) {
          toast(message)
        }
        reject(error)
      },
      fail(err) {
        const error = new Error(normalizeNetworkError(err))
        logRequestFailed({
          requestId,
          method: requestMethod,
          url: requestUrl,
          durationMs: nowMs() - startedAt,
          error
        })
        if (!skipErrorHandler) toast(error.message)
        reject(error)
      }
    })
  })
}

export function uploadFile(options = {}) {
  const {
    url,
    filePath,
    name = 'file',
    formData = {},
    header = {},
    timeout = 60000,
    skipErrorHandler = false
  } = options
  const requestId = header['X-Request-ID'] || header['x-request-id'] || createRequestId()
  const requestUrl = joinUrl(url)
  const startedAt = nowMs()
  logRequestStarted({ requestId, method: 'POST', url: requestUrl, upload: true })

  return new Promise((resolve, reject) => {
    uni.uploadFile({
      url: requestUrl,
      filePath,
      name,
      formData,
      timeout,
      header: {
        ...getAuthHeader(),
        'X-Request-ID': requestId,
        ...header
      },
      success(res) {
        const status = Number(res.statusCode || 0)
        const durationMs = nowMs() - startedAt
        let payload = res.data
        try {
          payload = typeof res.data === 'string' ? JSON.parse(res.data) : res.data
        } catch {
          payload = res.data
        }

        if (status >= 200 && status < 300) {
          logRequestCompleted({
            requestId,
            method: 'POST',
            url: requestUrl,
            statusCode: status,
            durationMs,
            upload: true
          })
          resolve(payload)
          return
        }

        const message = normalizeErrorMessage(payload, status >= 500 ? '服务暂时不可用' : '上传失败')
        const error = new Error(message)
        error.statusCode = status
        error.data = payload
        logRequestFailed({
          requestId,
          method: 'POST',
          url: requestUrl,
          statusCode: status,
          durationMs,
          error,
          upload: true
        })
        if (status === 401) {
          handleUnauthorized()
        } else if (!skipErrorHandler) {
          toast(message)
        }
        reject(error)
      },
      fail(err) {
        const error = new Error(normalizeNetworkError(err))
        logRequestFailed({
          requestId,
          method: 'POST',
          url: requestUrl,
          durationMs: nowMs() - startedAt,
          error,
          upload: true
        })
        if (!skipErrorHandler) toast(error.message)
        reject(error)
      }
    })
  })
}
