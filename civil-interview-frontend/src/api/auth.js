import { http } from './index'

export async function login(username, password) {
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
  return http.post('/register', form, {
    skipErrorHandler: true
  })
}

export async function getWechatWebLoginUrl() {
  return http.get('/auth/wechat/web/url', {
    skipErrorHandler: true
  })
}

// Password reset is intentionally hidden on PC for now. Keep the endpoints
// inactive here so no visible PC flow can call the unfinished reset service.
// export async function requestPasswordReset(data) {
//   return http.post('/password-reset/request', data, {
//     skipErrorHandler: true
//   })
// }
//
// export async function verifyPasswordReset(data) {
//   return http.post('/password-reset/verify', data, {
//     skipErrorHandler: true
//   })
// }
//
// export async function confirmPasswordReset(data) {
//   return http.post('/password-reset/confirm', data, {
//     skipErrorHandler: true
//   })
// }
