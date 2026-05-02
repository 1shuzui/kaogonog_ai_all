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
