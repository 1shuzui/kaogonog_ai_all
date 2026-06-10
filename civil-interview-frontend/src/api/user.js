/**
 * 用户资料接口封装，集中读取账户、偏好、安全设置和管理员标记。
 *
 * 省份偏好和考试体系偏好只影响默认筛选，不改变题库真实分类；管理员标识也必须来自后端，
 * 页面不能靠本地缓存自行判断后台权限。
 *
 * @param data: 用户资料、偏好、省份、密码或协议确认请求体。
 * @return Promise，解析用户资料、省份列表、偏好更新或安全设置结果。
 * @raises AxiosError: 未登录、权限不足、密码错误或接口失败会抛给调用页面。
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
