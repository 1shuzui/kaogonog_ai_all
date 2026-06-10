/**
 * 倒计时组合函数服务读题、准备和答题阶段，统一处理暂停、重置和结束回调，避免不同考场页对时间边界理解不一致。
 *
 * 计时只负责 UI 与流程推进，不决定题目分值、权益消耗或考试是否有效；这些判断应由考场流程和后端结果确认。
 *
 * @param 无；导出的 useCountdown 接收初始秒数，运行时可重置新的总时长。
 * @return 导出剩余时间、进度、格式化文本和 start/pause/stop/reset/onFinish 操作。
 * @raises 浏览器权限、网络和运行时异常按函数内部策略提示或交由调用方处理。
 */
import { ref, computed, onUnmounted } from 'vue'
import { formatTime } from '@/utils/formatter'

export function useCountdown(initialSeconds = 0) {
  const remaining = ref(initialSeconds)
  const total = ref(initialSeconds)
  const isRunning = ref(false)
  const isFinished = ref(false)

  let intervalId = null
  let lastTick = 0
  let finishCallback = null

  const progress = computed(() => {
    if (total.value <= 0) return 0
    return Math.round((remaining.value / total.value) * 100)
  })

  const formattedTime = computed(() => formatTime(remaining.value))

  function start() {
    if (isRunning.value) return
    isRunning.value = true
    isFinished.value = false
    lastTick = performance.now()

    intervalId = setInterval(() => {
      const now = performance.now()
      const elapsed = Math.floor((now - lastTick) / 1000)
      if (elapsed >= 1) {
        remaining.value = Math.max(0, remaining.value - elapsed)
        lastTick = now
        if (remaining.value <= 0) {
          stop()
          isFinished.value = true
          finishCallback?.()
        }
      }
    }, 200)
  }

  function stop() {
    clearInterval(intervalId)
    intervalId = null
    isRunning.value = false
  }

  function pause() {
    stop()
  }

  function reset(newTotal) {
    stop()
    if (newTotal !== undefined) {
      total.value = newTotal
    }
    remaining.value = total.value
    isFinished.value = false
  }

  function onFinish(callback) {
    finishCallback = callback
  }

  onUnmounted(() => stop())

  return {
    remaining,
    total,
    progress,
    formattedTime,
    isRunning,
    isFinished,
    start,
    pause,
    stop,
    reset,
    onFinish
  }
}
