/**
 * 这个接口文件负责用户资料、省份和偏好接口封装；页面只调用这里的方法，避免到处拼 URL 和重复处理错误。
 *
 * @param 无；文件级模块依赖导出函数、组合式 API 或调用方传入上下文。
 * @return 导出可复用的端侧能力，具体返回值由各公共函数保持兼容。
 * @raises 不主动吞掉业务异常；请求失败、权限不足和运行时错误交由调用方或全局拦截器处理。
 */
import { http } from './index'

export async function getUserInfo(config = {}) {
  return http.get('/user/info', config)
}

export async function updatePreferences(data) {
  return http.put('/user/preferences', data)
}

export async function updateUserProfile(data) {
  return http.put('/user/profile', data)
}

export async function getProvinces() {
  return http.get('/user/provinces')
}

export async function getTermsStatus(config = {}) {
  return http.get('/user/terms-status', config)
}

export async function agreeTerms(version) {
  return http.post('/user/agree-terms', { version })
}

export async function updatePassword(data) {
  return http.put('/user/password', data)
}

export async function getDeviceRisk(deviceId, config = {}) {
  return http.get('/user/device-risk', {
    headers: { 'X-Device-ID': deviceId || '' },
    ...config
  })
}
