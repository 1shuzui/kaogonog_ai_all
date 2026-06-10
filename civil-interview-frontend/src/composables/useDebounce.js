/**
 * 防抖组合函数让题库搜索、筛选器和按钮节流共享同一套取消语义，避免重复请求把列表状态冲乱。
 *
 * 它不吞掉业务错误，也不负责接口重试；被防抖的函数仍应在调用处处理权限、空态和错误提示。
 *
 * @param 无；导出的 useDebounce 接收待执行函数和延迟毫秒数。
 * @return 导出 run、cancel 和 pending 状态，供输入框与按钮复用。
 * @raises 浏览器权限、网络和运行时异常按函数内部策略提示或交由调用方处理。
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
