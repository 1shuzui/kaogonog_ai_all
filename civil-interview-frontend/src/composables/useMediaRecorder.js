import { ref, onUnmounted } from 'vue'

function getSupportedMimeType(hasVideo) {
  const videoTypes = [
    'video/webm;codecs=vp9,opus',
    'video/webm;codecs=vp8,opus',
    'video/webm',
    'video/mp4'
  ]
  const audioTypes = [
    'audio/webm;codecs=opus',
    'audio/webm',
    'audio/ogg;codecs=opus',
    'audio/mp4'
  ]
  const types = hasVideo ? videoTypes : audioTypes
  for (const type of types) {
    if (typeof MediaRecorder !== 'undefined' && MediaRecorder.isTypeSupported(type)) {
      return type
    }
  }
  return ''
}

export function useMediaRecorder() {
  const stream = ref(null)
  const isRecording = ref(false)
  const isPaused = ref(false)
  const duration = ref(0)
  const error = ref('')
  const hasVideo = ref(true)

  let mediaRecorder = null
  let chunks = []
  let durationTimer = null
  let startTime = 0

  async function initStream(opts = {}) {
    try {
      const enableVideo = opts.videoEnabled !== false
      hasVideo.value = enableVideo
      const constraints = {
        audio: {
          echoCancellation: true,
          noiseSuppression: true
        }
      }
      if (enableVideo) {
        constraints.video = {
          width: { ideal: 640 },
          height: { ideal: 480 },
          facingMode: 'user'
        }
      }
      stream.value = await navigator.mediaDevices.getUserMedia(constraints)
      error.value = ''
      return stream.value
    } catch (e) {
      error.value = '获取媒体设备失败: ' + e.message
      return null
    }
  }

  function startRecording() {
    if (!stream.value) {
      error.value = '请先初始化媒体流'
      return false
    }

    clearInterval(durationTimer)
    duration.value = 0
    error.value = ''
    chunks = []
    const mimeType = getSupportedMimeType(hasVideo.value)
    const recorderOptions = mimeType ? { mimeType } : {}

    try {
      mediaRecorder = new MediaRecorder(stream.value, recorderOptions)
    } catch (e) {
      error.value = '创建录制器失败: ' + e.message
      return false
    }

    mediaRecorder.ondataavailable = (e) => {
      if (e.data.size > 0) chunks.push(e.data)
    }

    mediaRecorder.onerror = (e) => {
      error.value = '录制出错'
      isRecording.value = false
    }

    mediaRecorder.start(1000) // 每秒收集一次数据
    isRecording.value = true
    isPaused.value = false
    startTime = performance.now()

    durationTimer = setInterval(() => {
      if (!isPaused.value) {
        duration.value = Math.floor((performance.now() - startTime) / 1000)
      }
    }, 200)
    return true
  }

  function stopRecording() {
    return new Promise((resolve) => {
      if (!mediaRecorder || mediaRecorder.state === 'inactive') {
        isRecording.value = false
        resolve(null)
        return
      }

      const currentRecorder = mediaRecorder
      currentRecorder.onstop = () => {
        clearInterval(durationTimer)
        isRecording.value = false
        isPaused.value = false
        const mimeType = getSupportedMimeType(hasVideo.value) || (hasVideo.value ? 'video/webm' : 'audio/webm')
        const blob = new Blob(chunks, { type: mimeType })
        mediaRecorder = null
        chunks = []
        resolve(blob.size > 0 ? blob : null)
      }

      try {
        currentRecorder.requestData?.()
      } catch {}

      currentRecorder.stop()
    })
  }

  function pauseRecording() {
    if (mediaRecorder?.state === 'recording') {
      mediaRecorder.pause()
      isPaused.value = true
    }
  }

  function resumeRecording() {
    if (mediaRecorder?.state === 'paused') {
      mediaRecorder.resume()
      isPaused.value = false
    }
  }

  function destroyStream() {
    if (mediaRecorder && mediaRecorder.state !== 'inactive') {
      try {
        mediaRecorder.stop()
      } catch {}
    }
    if (stream.value) {
      stream.value.getTracks().forEach(t => t.stop())
      stream.value = null
    }
    mediaRecorder = null
    chunks = []
    clearInterval(durationTimer)
    isRecording.value = false
    isPaused.value = false
    duration.value = 0
  }

  onUnmounted(() => {
    destroyStream()
  })

  return {
    stream,
    isRecording,
    isPaused,
    duration,
    error,
    initStream,
    startRecording,
    stopRecording,
    pauseRecording,
    resumeRecording,
    destroyStream
  }
}
