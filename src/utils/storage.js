// 安全的 localStorage 操作
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
      console.warn(`[Storage] 读取 ${key} 失败:`, e)
      return defaultValue
    }
  },

  set(key, value) {
    if (!isStorageAvailable()) return false
    try {
      localStorage.setItem(key, JSON.stringify(value))
      return true
    } catch (e) {
      console.warn(`[Storage] 保存 ${key} 失败:`, e)
      return false
    }
  },

  remove(key) {
    if (!isStorageAvailable()) return false
    try {
      localStorage.removeItem(key)
      return true
    } catch (e) {
      console.warn(`[Storage] 删除 ${key} 失败:`, e)
      return false
    }
  }
}
