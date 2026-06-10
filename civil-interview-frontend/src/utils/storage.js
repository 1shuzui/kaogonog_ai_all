/**
 * PC 本地存储工具为 token、偏好和临时状态提供安全读写封装，避免隐私模式或配额异常直接打断页面。
 *
 * 本地缓存只是体验优化，不能作为权益、支付成功或管理员权限的可信来源；读取失败时返回默认值，让页面回到服务端校验流程。
 *
 * @param 无；导出方法接收 storage key、默认值和待写入值。
 * @return 导出容错的 get、set、remove 方法，供 store 和页面复用。
 * @raises 参数异常通常返回兜底值；需要阻断流程的错误交由调用方处理。
 */
// 安全的 localStorage 操作
import { logger } from '@/utils/logger'

const isStorageAvailable = () => {
  try {
    const test = '__test__'
    localStorage.setItem(test, test)
    localStorage.removeItem(test)
    return true
  } catch (e) {
    return false
  }
}

export const storage = {
  get(key, defaultValue = null) {
    if (!isStorageAvailable()) return defaultValue
    try {
      const item = localStorage.getItem(key)
      return item ? JSON.parse(item) : defaultValue
    } catch (e) {
      logger.warn('Storage read failed', {
        event: 'storage.read.failed',
        key,
        error: e
      })
      return defaultValue
    }
  },

  set(key, value) {
    if (!isStorageAvailable()) return false
    try {
      localStorage.setItem(key, JSON.stringify(value))
      return true
    } catch (e) {
      logger.warn('Storage write failed', {
        event: 'storage.write.failed',
        key,
        error: e
      })
      return false
    }
  },

  remove(key) {
    if (!isStorageAvailable()) return false
    try {
      localStorage.removeItem(key)
      return true
    } catch (e) {
      logger.warn('Storage remove failed', {
        event: 'storage.remove.failed',
        key,
        error: e
      })
      return false
    }
  }
}
