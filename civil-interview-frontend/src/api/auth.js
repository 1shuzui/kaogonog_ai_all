import { http, USE_MOCK } from './index'
import { mockLogin, mockRegister } from './mock/auth'

export async function login(username, password) {
  if (USE_MOCK) return mockLogin(username, password)
  // Backend uses OAuth2PasswordRequestForm, requires x-www-form-urlencoded
  const params = new URLSearchParams()
  params.append('username', username)
  params.append('password', password)
  return http.post('/token', params, {
    headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
    skipErrorHandler: true
  })
}

export async function register(form) {
  if (USE_MOCK) return mockRegister(form)
  return http.post('/register', form, {
    skipErrorHandler: true
  })
}

export async function requestPasswordReset(data) {
  return http.post('/password-reset/request', data, {
    skipErrorHandler: true
  })
}

export async function verifyPasswordReset(data) {
  return http.post('/password-reset/verify', data, {
    skipErrorHandler: true
  })
}

export async function confirmPasswordReset(data) {
  return http.post('/password-reset/confirm', data, {
    skipErrorHandler: true
  })
}
