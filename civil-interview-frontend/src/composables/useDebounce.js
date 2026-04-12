import { ref, onUnmounted } from 'vue'

/**
 * 防抖 composable
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
