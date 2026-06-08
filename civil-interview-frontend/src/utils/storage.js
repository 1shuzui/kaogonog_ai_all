/**
 * 这个工具文件处理 `storage` 这类跨页面规则；集中维护可以避免 PC、小程序或不同页面各自写一份判断。
 *
 * @param 无；文件级模块依赖导出函数、组合式 API 或调用方传入上下文。
 * @return 导出可复用的端侧能力，具体返回值由各公共函数保持兼容。
 * @raises 不主动吞掉业务异常；请求失败、权限不足和运行时错误交由调用方或全局拦截器处理。
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
