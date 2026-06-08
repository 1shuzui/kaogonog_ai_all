/**
 * 这个接口文件负责登录、注册和微信账号相关接口封装；页面只调用这里的方法，避免到处拼 URL 和重复处理错误。
 *
 * @param 无；文件级模块依赖导出函数、组合式 API 或调用方传入上下文。
 * @return 导出可复用的端侧能力，具体返回值由各公共函数保持兼容。
 * @raises 不主动吞掉业务异常；请求失败、权限不足和运行时错误交由调用方或全局拦截器处理。
 */
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

export function loginWithWechat(code, agreedTermsVersion) {
  return request({
    url: '/auth/wechat/miniprogram',
    method: 'POST',
    data: {
      code,
      agreedTermsVersion
    },
    timeout: 15000,
    skipErrorHandler: true
  })
}

export function bindWechatMiniProgram(code) {
  return request({
    url: '/auth/wechat/miniprogram/bind',
    method: 'POST',
    data: { code },
    timeout: 15000,
    skipErrorHandler: true
  })
}

export function setupWechatMiniProgramAccount(data) {
  return request({
    url: '/auth/wechat/miniprogram/account',
    method: 'POST',
    data,
    timeout: 15000,
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
