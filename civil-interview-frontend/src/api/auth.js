/**
 * 这个接口文件负责登录、注册和微信账号相关接口封装；页面只调用这里的方法，避免到处拼 URL 和重复处理错误。
 *
 * @param 无；文件级模块依赖导出函数、组合式 API 或调用方传入上下文。
 * @return 导出可复用的端侧能力，具体返回值由各公共函数保持兼容。
 * @raises 不主动吞掉业务异常；请求失败、权限不足和运行时错误交由调用方或全局拦截器处理。
 */
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
