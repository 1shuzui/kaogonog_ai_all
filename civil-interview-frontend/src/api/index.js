import axios from 'axios'
import { message } from 'ant-design-vue'
import router from '@/router'

const USE_MOCK = import.meta.env.VITE_USE_MOCK === 'true'

const http = axios.create({
  baseURL: import.meta.env.VITE_API_BASE || '/api',
  timeout: 180000
})

function normalizeErrorMessage(payload) {
  const detail = payload?.detail ?? payload?.message ?? payload

  if (Array.isArray(detail)) {
    const items = detail
      .map(item => {
        if (typeof item === 'string') return item
        if (item?.msg && item?.loc?.length) return `${item.loc.join(' -> ')}: ${item.msg}`
        if (item?.msg) return item.msg
        return ''
      })
      .filter(Boolean)
    return items.join('；') || '请求失败'
  }

  if (detail && typeof detail === 'object') {
    if (typeof detail.msg === 'string') return detail.msg
    if (typeof detail.message === 'string') return detail.message
    return Object.values(detail)
      .flat()
      .map(value => (typeof value === 'string' ? value : ''))
      .filter(Boolean)
      .join('；') || '请求失败'
  }

  return detail ? String(detail) : '请求失败'
}

http.interceptors.request.use((config) => {
  const token = localStorage.getItem('token')
  if (token) {
    config.headers.Authorization = `Bearer ${token}`
  }
  return config
})

http.interceptors.response.use(
  (res) => res.data,
  (err) => {
    if (err.response?.status === 401) {
      localStorage.removeItem('token')
      localStorage.removeItem('username')
      message.warning('登录状态已失效，请重新登录')
      if (router.currentRoute.value.path !== '/login') {
        router.push({ path: '/login', query: { redirect: router.currentRoute.value.fullPath } })
      }
      return Promise.reject(err)
    }
    const msg = normalizeErrorMessage(err.response?.data || err.message)
    message.error(msg)
    return Promise.reject(err)
  }
)

export { http, USE_MOCK }
export default http
