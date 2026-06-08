/**
 * 这个文件集中处理小程序跳转、登录提示和 loading；未登录用户可以浏览，但触发试用、练习或支付时必须在这里被拦住。
 *
 * @param 无；文件级模块依赖导出函数、组合式 API 或调用方传入上下文。
 * @return 导出可复用的端侧能力，具体返回值由各公共函数保持兼容。
 * @raises 不主动吞掉业务异常；请求失败、权限不足和运行时错误交由调用方或全局拦截器处理。
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
