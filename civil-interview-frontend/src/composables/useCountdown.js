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
