import { ref, onUnmounted } from 'vue'

export function useSpeechRecognition() {
  const finalTranscript = ref('')
  const interimTranscript = ref('')
  const active = ref(false)
  const error = ref('')

  const RecognitionCtor = typeof window !== 'undefined'
    ? (window.SpeechRecognition || window.webkitSpeechRecognition)
    : null

  let recognition = null
  let stopResolver = null
  let stopFallbackTimer = null

  function combinedTranscript() {
    return `${finalTranscript.value}${interimTranscript.value}`.trim()
  }

  function reset() {
    finalTranscript.value = ''
    interimTranscript.value = ''
    error.value = ''
  }

  function cleanupStopResolver() {
    if (stopFallbackTimer) {
      clearTimeout(stopFallbackTimer)
      stopFallbackTimer = null
    }
    stopResolver = null
  }

  function resolveStop() {
    if (typeof stopResolver === 'function') {
      const resolver = stopResolver
      cleanupStopResolver()
      resolver(combinedTranscript())
    }
  }

  function ensureRecognition() {
    if (!RecognitionCtor) {
      error.value = '当前浏览器不支持语音识别'
      return null
    }
    if (!recognition) {
      recognition = new RecognitionCtor()
      recognition.lang = 'zh-CN'
      recognition.continuous = true
      recognition.interimResults = true
      recognition.maxAlternatives = 1

      recognition.onresult = (event) => {
        let nextFinal = finalTranscript.value
        let nextInterim = ''
        for (let i = event.resultIndex; i < event.results.length; i++) {
          const segment = event.results[i]?.[0]?.transcript || ''
          if (event.results[i].isFinal) {
            nextFinal += segment
          } else {
            nextInterim += segment
          }
        }
        finalTranscript.value = nextFinal
        interimTranscript.value = nextInterim
      }

      recognition.onerror = (event) => {
        error.value = event?.error || 'speech_recognition_failed'
      }

      recognition.onstart = () => {
        active.value = true
      }

      recognition.onend = () => {
        active.value = false
        resolveStop()
      }
    }
    return recognition
  }

  function start() {
    reset()
    const instance = ensureRecognition()
    if (!instance) return false
    try {
      instance.start()
      return true
    } catch {
      return false
    }
  }

  function stop() {
    return new Promise((resolve) => {
      stopResolver = resolve
      if (!recognition || !active.value) {
        resolveStop()
        return
      }

      stopFallbackTimer = setTimeout(() => {
        active.value = false
        resolveStop()
      }, 1200)

      try {
        recognition.stop()
      } catch {
        active.value = false
        resolveStop()
      }
    })
  }

  onUnmounted(() => {
    stop().catch(() => {})
  })

  return {
    supported: !!RecognitionCtor,
    active,
    error,
    finalTranscript,
    interimTranscript,
    start,
    stop,
    reset,
    combinedTranscript
  }
}
