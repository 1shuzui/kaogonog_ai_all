/**
 * 这个组合式函数封装 `useDebounce` 相关浏览器行为；页面复用它，是为了少碰底层 API 和生命周期细节。
 *
 * @param 无；文件级模块依赖导出函数、组合式 API 或调用方传入上下文。
 * @return 导出可复用的端侧能力，具体返回值由各公共函数保持兼容。
 * @raises 不主动吞掉业务异常；请求失败、权限不足和运行时错误交由调用方或全局拦截器处理。
 */
import { ref, onUnmounted } from 'vue'

/**
 * 将防抖状态封装为 composable，是为了让输入框、筛选器和按钮节流共享同一套取消语义。
 *
 * @param {Function} fn - 要防抖的函数
 * @param {number} delay - 延迟时间（ms）
 * @returns {{ run: Function, cancel: Function, pending: Ref<boolean> }}
 */
export function useDebounce(fn, delay = 300) {
  const pending = ref(false)
  let timer = null

  function run(...args) {
    cancel()
    pending.value = true
    timer = setTimeout(() => {
      pending.value = false
      fn(...args)
    }, delay)
  }

  function cancel() {
    if (timer) {
      clearTimeout(timer)
      timer = null
      pending.value = false
    }
  }

  onUnmounted(cancel)

  return { run, cancel, pending }
}
