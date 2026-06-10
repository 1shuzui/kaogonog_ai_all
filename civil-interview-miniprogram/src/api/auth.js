/**
 * 登录注册接口封装，统一处理账号密码、微信登录和找回密码调用，让页面不直接拼认证路径。
 *
 * 小程序审核要求先浏览后登录，所以这些函数只能由登录页或明确需要账号的动作触发；
 * 微信 code、协议版本和 PC 账号补全都交给后端绑定，页面不要直接持久化 openId。
 *
 * @param username: 账号密码登录、注册、找回密码或账号补全时使用的用户名。
 * @param password: 登录、注册或补全账号时使用的明文密码，由后端统一哈希。
 * @return Promise，解析 token、用户资料、微信登录状态或密码重置结果。
 * @raises Error: 认证失败、验证码错误、账号冲突或网络异常会由 request 层规范化后抛出。
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
