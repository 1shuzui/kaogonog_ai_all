/**
 * 用户资料接口封装，集中读取账户、偏好、安全设置和管理员标记。
 *
 * 用户省份和考试体系偏好只影响默认筛选，不会改题库真实分类；
 * 管理员标记必须来自后端，页面不能因为本地 storage 残留就显示后台入口。
 *
 * @param data: 用户资料、偏好、省份、密码或协议确认请求体。
 * @return Promise，解析用户资料、省份列表、偏好更新或安全设置结果。
 * @raises Error: 未登录、权限不足、密码错误或接口失败会由 request 层抛出。
 */
import { request } from './request'

export function getUserInfo(config = {}) {
  return request({
    url: '/user/info',
    ...config
  })
}

export function getProvinces() {
  return request({
    url: '/user/provinces'
  })
}

export function updatePreferences(data) {
  return request({
    url: '/user/preferences',
    method: 'PUT',
    data
  })
}

export function updateUserProfile(data) {
  return request({
    url: '/user/profile',
    method: 'PUT',
    data
  })
}

export function updatePassword(data) {
  return request({
    url: '/user/password',
    method: 'PUT',
    data
  })
}

export function getTermsStatus(config = {}) {
  return request({
    url: '/user/terms-status',
    ...config
  })
}

export function agreeTerms(version) {
  return request({
    url: '/user/agree-terms',
    method: 'POST',
    data: { version }
  })
}

export function getDeviceRisk(deviceId, config = {}) {
  return request({
    url: '/user/device-risk',
    header: {
      'X-Device-ID': deviceId || ''
    },
    ...config
  })
}
