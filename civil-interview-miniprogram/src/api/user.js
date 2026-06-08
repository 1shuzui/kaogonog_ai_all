/**
 * 这个接口文件负责用户资料、省份和偏好接口封装；页面只调用这里的方法，避免到处拼 URL 和重复处理错误。
 *
 * @param 无；文件级模块依赖导出函数、组合式 API 或调用方传入上下文。
 * @return 导出可复用的端侧能力，具体返回值由各公共函数保持兼容。
 * @raises 不主动吞掉业务异常；请求失败、权限不足和运行时错误交由调用方或全局拦截器处理。
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
