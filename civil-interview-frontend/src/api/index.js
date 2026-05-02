import axios from 'axios'
import { message } from 'ant-design-vue'
import router from '@/router'
import { normalizeScoringErrorMessage } from '@/utils/scoringSupport'

const USE_MOCK = import.meta.env.VITE_USE_MOCK === 'true'
const TOKEN_STORAGE_KEY = 'token'
const USERNAME_STORAGE_KEY = 'username'

const http = axios.create({
  baseURL: import.meta.env.VITE_API_BASE || '/api',
  timeout: 180000
})

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
  const token = localStorage.getItem(TOKEN_STORAGE_KEY)
  if (token) {
    config.headers.Authorization = `Bearer ${token}`
  }
  return config
})

http.interceptors.response.use(
  (res) => res.data,
  (err) => {
    const { response, config = {} } = err
    const status = response?.status || 0
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

export { http, USE_MOCK }
export default http
