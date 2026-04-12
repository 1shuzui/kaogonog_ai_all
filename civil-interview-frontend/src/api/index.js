import axios from 'axios'
import { message } from 'ant-design-vue'
import router from '@/router'

const USE_MOCK = import.meta.env.VITE_USE_MOCK === 'true'

const http = axios.create({
  baseURL: import.meta.env.VITE_API_BASE || '/api',
  timeout: 60000  // AI评分可能需要较长时间，增加到60秒
})

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
      if (router.currentRoute.value.path !== '/login') {
        router.push({ path: '/login', query: { redirect: router.currentRoute.value.fullPath } })
      }
      return Promise.reject(err)
    }
    const msg = err.response?.data?.detail || err.response?.data?.message || err.message || '请求失败'
    message.error(msg)
    return Promise.reject(err)
  }
)

export { http, USE_MOCK }
export default http
