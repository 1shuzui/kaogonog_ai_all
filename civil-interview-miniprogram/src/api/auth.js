import { request } from './request'

export function login(username, password) {
  return request({
    url: '/token',
    method: 'POST',
    data: `username=${encodeURIComponent(username)}&password=${encodeURIComponent(password)}`,
    header: {
      'Content-Type': 'application/x-www-form-urlencoded'
    },
    timeout: 15000,
    skipErrorHandler: true
  })
}

export function register(data) {
  return request({
    url: '/register',
    method: 'POST',
    data,
    skipErrorHandler: true
  })
}

export function requestPasswordReset(data) {
  return request({
    url: '/password-reset/request',
    method: 'POST',
    data,
    skipErrorHandler: true
  })
}

export function verifyPasswordReset(data) {
  return request({
    url: '/password-reset/verify',
    method: 'POST',
    data,
    skipErrorHandler: true
  })
}

export function confirmPasswordReset(data) {
  return request({
    url: '/password-reset/confirm',
    method: 'POST',
    data,
    skipErrorHandler: true
  })
}
