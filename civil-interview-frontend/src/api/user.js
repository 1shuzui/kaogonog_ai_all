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
