/**
 * 小程序导航和交互提示工具，集中处理登录拦截、跳转方式、toast、loading 和确认弹窗。
 *
 * 微信审核要求“先浏览后登录”，所以页面进入时不要直接调用强制登录；只有用户点击试用、开始练习、开通套餐、
 * 我的、历史、收藏、订单或管理员功能时，才通过这里进入登录页。这样所有页面复用同一套 redirectUrl 逻辑，
 * 登录成功后能回到用户原本想做的动作。
 *
 * @param 各函数接收目标路径、提示文案、业务动作名称或 loading 配置。
 * @return 返回跳转/提示是否已触发，供页面决定是否继续执行业务请求。
 * @raises 不主动抛业务异常；uni API 调用失败时通常由运行时回调或页面兜底处理。
 */
import { TOKEN_STORAGE_KEY } from './constants'

export function hasToken() {
  try {
    return !!uni.getStorageSync(TOKEN_STORAGE_KEY)
  } catch {
    return false
  }
}

export function requireLogin() {
  if (hasToken()) return true
  uni.reLaunch({ url: '/pages/login/index' })
  return false
}

export function promptLoginForAction(actionName = '使用该功能', redirectUrl = '') {
  if (hasToken()) return true
  const action = String(actionName || '使用该功能')
  const redirect = String(redirectUrl || '')
  toast(`${action}需要先登录`)
  const query = redirect ? `?redirect=${encodeURIComponent(redirect)}` : ''
  uni.navigateTo({ url: `/pages/login/index${query}` })
  return false
}

export function toast(title, icon = 'none') {
  uni.showToast({
    title,
    icon,
    duration: 2200
  })
}

export function showLoading(title = '加载中') {
  uni.showLoading({
    title,
    mask: true
  })
}

export function hideLoading() {
  uni.hideLoading()
}
