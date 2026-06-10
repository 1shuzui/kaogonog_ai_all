/**
 * 登录注册接口封装，统一处理账号密码、微信登录和找回密码调用，让页面不直接拼认证路径。
 *
 * 账号密码登录仍走 OAuth2 表单格式；微信小程序登录和 PC 账号补全复用后端同一套账号体系，
 * 所以页面只传业务参数，不自行拼 token、协议版本或 openId 绑定逻辑。
 *
 * @param username: 账号密码登录、注册或找回密码时使用的账号。
 * @param password: 登录、注册或补全账号时使用的明文密码，由后端完成哈希。
 * @return Promise，解析后端返回的 token、用户信息或密码重置结果。
 * @raises AxiosError: 认证失败、验证码错误、账号冲突或网络异常会由请求层抛给页面处理。
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
