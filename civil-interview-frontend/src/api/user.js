import { http, USE_MOCK } from './index'
import { getMockUserInfo, getMockProvinces } from './mock/user'

export async function getUserInfo() {
  if (USE_MOCK) return getMockUserInfo()
  return http.get('/user/info')
}

export async function updatePreferences(data) {
  if (USE_MOCK) return { success: true }
  return http.put('/user/preferences', data)
}

export async function getProvinces() {
  if (USE_MOCK) return getMockProvinces()
  return http.get('/user/provinces')
}
