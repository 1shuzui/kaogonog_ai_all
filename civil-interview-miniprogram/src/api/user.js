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
