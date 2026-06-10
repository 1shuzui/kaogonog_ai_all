/**
 * 网络状态组合函数给考场、支付和提交页面提供在线/离线提示，避免用户误以为按钮失效。
 *
 * 它只监听浏览器网络事件，不重试接口也不缓存提交内容；真正的重试和错误恢复应由调用页面按业务场景决定。
 *
 * @param 无；组合函数不需要外部参数。
 * @return 导出当前在线状态和是否曾离线的标记。
 * @raises 浏览器权限、网络和运行时异常按函数内部策略提示或交由调用方处理。
 */
import { ref, onMounted, onUnmounted } from 'vue'

/**
 * 网络状态监控 composable
 * 用于检测用户在线/离线状态，适合在考试等关键页面使用
 */
export function useNetworkStatus() {
  const isOnline = ref(navigator.onLine)
  const wasOffline = ref(false)

  function handleOnline() {
    isOnline.value = true
  }

  function handleOffline() {
    isOnline.value = false
    wasOffline.value = true
  }

  onMounted(() => {
    window.addEventListener('online', handleOnline)
    window.addEventListener('offline', handleOffline)
  })

  onUnmounted(() => {
    window.removeEventListener('online', handleOnline)
    window.removeEventListener('offline', handleOffline)
  })

  return { isOnline, wasOffline }
}
