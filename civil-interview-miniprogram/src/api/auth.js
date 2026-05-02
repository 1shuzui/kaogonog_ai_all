import { request } from './request'

export function login(username, password) {
  return request({
    url: '/token',
    method: 'POST',
    data: `username=${encodeURIComponent(username)}&password=${encodeURIComponent(password)}`,
    header: {
      'Content-Type': 'application/x-www-form-urlencoded'
    },
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
