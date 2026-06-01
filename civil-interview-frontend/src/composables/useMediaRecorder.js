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
  let externallyOwned = false

  function setStream(externalStream) {
    if (externalStream) {
      stream.value = externalStream
      hasVideo.value = externalStream.getVideoTracks().length > 0
      error.value = ''
      externallyOwned = true  // stream owned externally, don't destroy on unmount
    }
  }

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
      externallyOwned = false  // we created this stream, own it
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
      return
    }

    // Guard: if MediaRecorder already active, stop it first
    if (mediaRecorder && mediaRecorder.state !== 'inactive') {
      mediaRecorder.stop()
      mediaRecorder = null
    }

    // Guard: if stream has no active tracks, re-init
    const activeTracks = stream.value.getTracks().filter(t => t.readyState === 'live')
    if (!activeTracks.length) {
      error.value = '媒体流已断开，请刷新页面后重试'
      return
    }

    chunks = []
    const mimeType = getSupportedMimeType(hasVideo.value)
    const recorderOptions = mimeType ? { mimeType } : {}

    try {
      mediaRecorder = new MediaRecorder(stream.value, recorderOptions)
    } catch (e) {
      error.value = '创建录制器失败: ' + e.message
      return
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
  }

  function stopRecording() {
    return new Promise((resolve) => {
      if (!mediaRecorder || mediaRecorder.state === 'inactive') {
        resolve(null)
        return
      }

      mediaRecorder.onstop = () => {
        clearInterval(durationTimer)
        isRecording.value = false
        isPaused.value = false
        const mimeType = getSupportedMimeType(hasVideo.value) || (hasVideo.value ? 'video/webm' : 'audio/webm')
        const blob = new Blob(chunks, { type: mimeType })
        chunks = []
        resolve(blob)
      }

      mediaRecorder.stop()
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
    if (stream.value) {
      stream.value.getTracks().forEach(t => t.stop())
      stream.value = null
    }
    clearInterval(durationTimer)
    mediaRecorder = null
    isRecording.value = false
    isPaused.value = false
    duration.value = 0
  }

  function cleanupRecording() {
    clearInterval(durationTimer)
    mediaRecorder = null
    isRecording.value = false
    isPaused.value = false
    duration.value = 0
  }

  onUnmounted(() => {
    if (externallyOwned) {
      // Stream is owned externally (e.g. examStore.mediaStream) – don't stop tracks
      cleanupRecording()
    } else {
      destroyStream()
    }
  })

  return {
    stream,
    isRecording,
    isPaused,
    duration,
    error,
    setStream,
    initStream,
    startRecording,
    stopRecording,
    pauseRecording,
    resumeRecording,
    destroyStream
  }
}
