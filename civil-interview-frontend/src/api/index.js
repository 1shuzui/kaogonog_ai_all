/**
 * PC 端 HTTP 客户端总入口，统一处理 API 基础地址、token 注入、请求追踪、错误提示和登录失效跳转。
 *
 * 页面和 store 不应该直接 new axios；统一入口能保证管理员接口、支付接口、评分接口和普通题库接口拿到同样的鉴权头与超时设置。
 * 评分/ASR 请求可能耗时更长，所以这里的 timeout 比普通页面交互更宽；请求失败会转成可读消息，减少每个页面重复写错误分支。
 *
 * @param 无；具体请求参数由各业务 API 模块传入。
 * @return 导出配置好的 axios 实例和基于该实例的请求能力。
 * @raises AxiosError: 网络失败、401/403、后端业务错误或超时会通过拦截器规范化后继续抛给调用方。
 */
import axios from 'axios'
import { message } from 'ant-design-vue'
import router from '@/router'
import { normalizeScoringErrorMessage } from '@/utils/scoringSupport'
import { createRequestId, logger } from '@/utils/logger'

const TOKEN_STORAGE_KEY = 'token'
const USERNAME_STORAGE_KEY = 'username'

const http = axios.create({
  baseURL: import.meta.env.VITE_API_BASE || 'https://xzqianmianyuzhoukeji.com/api',
  timeout: 180000
})

function nowMs() {
  return typeof performance !== 'undefined' && performance.now ? performance.now() : Date.now()
}

function requestDurationMs(config = {}) {
  const startedAt = config.metadata?.started_at
  return startedAt ? Math.round((nowMs() - startedAt) * 100) / 100 : undefined
}

function logApiCompleted(config = {}, statusCode = 0, error = null) {
  const metadata = {
    event: error ? 'api.request.failed' : 'api.request.completed',
    request_id: config.metadata?.request_id,
    user_id: localStorage.getItem(USERNAME_STORAGE_KEY) || '',
    method: String(config.method || 'GET').toUpperCase(),
    url: config.url,
    status_code: statusCode,
    duration_ms: requestDurationMs(config)
  }

  if (error) {
    const write = statusCode >= 500 || statusCode === 0 ? logger.error : logger.warn
    write('API request failed', {
      ...metadata,
      error
    })
    return
  }

  logger.debug('API request completed', metadata)
}

export function normalizeErrorMessage(payload, fallback = 'Request failed') {
  const detail = payload?.detail ?? payload?.message ?? payload

  if (Array.isArray(detail)) {
    const items = detail
      .map((item) => {
        if (typeof item === 'string') return item
        if (item?.msg && item?.loc?.length) return `${item.loc.join(' -> ')}: ${item.msg}`
        if (item?.msg) return item.msg
        return ''
      })
      .filter(Boolean)

    return items.join('; ') || fallback
  }

  if (detail && typeof detail === 'object') {
    if (typeof detail.msg === 'string') return detail.msg
    if (typeof detail.message === 'string') return detail.message

    return Object.values(detail)
      .flat()
      .map((value) => (typeof value === 'string' ? value : ''))
      .filter(Boolean)
      .join('; ') || fallback
  }

  return normalizeScoringErrorMessage(detail ? String(detail) : fallback) || fallback
}

http.interceptors.request.use((config) => {
  const requestId = config.headers?.['X-Request-ID'] || config.headers?.['x-request-id'] || createRequestId()
  config.headers = config.headers || {}
  config.headers['X-Request-ID'] = requestId
  config.metadata = {
    ...(config.metadata || {}),
    request_id: requestId,
    started_at: nowMs()
  }
  const token = localStorage.getItem(TOKEN_STORAGE_KEY)
  if (token) {
    config.headers.Authorization = `Bearer ${token}`
  }
  logger.debug('API request started', {
    event: 'api.request.started',
    request_id: requestId,
    user_id: localStorage.getItem(USERNAME_STORAGE_KEY) || '',
    method: String(config.method || 'GET').toUpperCase(),
    url: config.url
  })
  return config
})

http.interceptors.response.use(
  (res) => {
    logApiCompleted(res.config, res.status)
    return res.data
  },
  (err) => {
    const { response, config = {} } = err
    const status = response?.status || 0
    logApiCompleted(config, status, err)
    const isSilentRequest = !!config.skipErrorHandler
    const fallbackMessage = !response
      ? '网络请求失败，请检查后端服务是否已启动'
      : status >= 500
        ? '服务暂时不可用，请稍后重试'
        : err.message || 'Request failed'
    const msg = normalizeErrorMessage(response?.data, fallbackMessage)
    err.normalizedMessage = msg

    if (err.response?.status === 401) {
      if (isSilentRequest) {
        return Promise.reject(err)
      }

      localStorage.removeItem(TOKEN_STORAGE_KEY)
      localStorage.removeItem(USERNAME_STORAGE_KEY)
      message.warning('Session expired, please log in again')
      if (router.currentRoute.value.path !== '/login') {
        router.push({ path: '/login', query: { redirect: router.currentRoute.value.fullPath } })
      }
      return Promise.reject(err)
    }

    if (!isSilentRequest) {
      message.error(msg)
    }
    return Promise.reject(err)
  }
)

export { http }
export default http
