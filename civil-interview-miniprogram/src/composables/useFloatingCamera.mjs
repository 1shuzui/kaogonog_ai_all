/** Own camera-window geometry and gestures; recording stays in the room. */
import { computed, ref, watch } from 'vue'

export function useFloatingCamera(runtime = {}) {
  const readNow = runtime.now || (() => Date.now())
  const getWindowInfo = runtime.getWindowInfo || (() => typeof wx !== 'undefined' && typeof wx.getWindowInfo === 'function' ? wx.getWindowInfo() : {})
  const cameraSize = ref('small')
  const cameraPosition = ref({ left: 0, top: 0 })
  let lastCameraTapAt = 0
  let cameraDragState = null
  let suppressCameraTapUntil = 0
  const cameraSizeClass = computed(() => `floating-camera--${cameraSize.value}`)
  const floatingCameraStyle = computed(() => {
    const position = cameraPosition.value
    return `left:${position.left}px;top:${position.top}px;`
  })

  const cameraSizeText = computed(() => {
    const labels = { small: '小窗', medium: '中窗', large: '大窗' }
    return `${labels[cameraSize.value] || '小窗'} · 可拖动`
  })

  function getWindowRect() {
    try {
      const info = getWindowInfo()
      return {
        width: Number(info.windowWidth || info.screenWidth || 375),
        height: Number(info.windowHeight || info.screenHeight || 667)
      }
    } catch {
      return { width: 375, height: 667 }
    }
  }

  function rpxToPx(value) {
    return (Number(value) || 0) * getWindowRect().width / 750
  }

  function getCameraPixelSize() {
    const sizes = {
      small: { width: 148, height: 198 },
      medium: { width: 212, height: 284 },
      large: { width: 284, height: 378 }
    }
    const size = sizes[cameraSize.value] || sizes.small
    return {
      width: rpxToPx(size.width),
      height: rpxToPx(size.height)
    }
  }

  function clampCameraPosition(position = cameraPosition.value) {
    const rect = getWindowRect()
    const size = getCameraPixelSize()
    const margin = rpxToPx(18)
    const maxLeft = Math.max(margin, rect.width - size.width - margin)
    const maxTop = Math.max(margin, rect.height - size.height - rpxToPx(128))
    cameraPosition.value = {
      left: Math.min(Math.max(Number(position.left) || margin, margin), maxLeft),
      top: Math.min(Math.max(Number(position.top) || margin, margin), maxTop)
    }
    return cameraPosition.value
  }

  function resetCameraPosition() {
    const rect = getWindowRect()
    const size = getCameraPixelSize()
    cameraPosition.value = clampCameraPosition({
      left: rect.width - size.width - rpxToPx(24),
      top: rect.height - size.height - rpxToPx(156)
    })
  }

  function ensureCameraPosition() {
    if (!cameraPosition.value.left && !cameraPosition.value.top) {
      resetCameraPosition()
    }
    return cameraPosition.value
  }

  function cycleCameraSize() {
    const order = ['small', 'medium', 'large']
    const currentIndex = order.indexOf(cameraSize.value)
    cameraSize.value = order[(currentIndex + 1) % order.length] || 'small'
  }

  function handleCameraTap() {
    if (readNow() < suppressCameraTapUntil) return
    const now = readNow()
    if (now - lastCameraTapAt < 320) {
      cycleCameraSize()
      lastCameraTapAt = 0
      return
    }
    lastCameraTapAt = now
  }

  function getTouchPoint(event) {
    const touch = event?.touches?.[0] || event?.changedTouches?.[0]
    if (!touch) return null
    return {
      x: Number(touch.clientX || touch.pageX || 0),
      y: Number(touch.clientY || touch.pageY || 0)
    }
  }

  function onCameraTouchStart(event) {
    const point = getTouchPoint(event)
    if (!point) return
    const position = ensureCameraPosition()
    cameraDragState = {
      startX: point.x,
      startY: point.y,
      originLeft: position.left,
      originTop: position.top,
      moved: false
    }
  }

  function onCameraTouchMove(event) {
    if (!cameraDragState) return
    const point = getTouchPoint(event)
    if (!point) return
    const dx = point.x - cameraDragState.startX
    const dy = point.y - cameraDragState.startY
    if (Math.abs(dx) > 3 || Math.abs(dy) > 3) {
      cameraDragState.moved = true
    }
    clampCameraPosition({
      left: cameraDragState.originLeft + dx,
      top: cameraDragState.originTop + dy
    })
  }

  function onCameraTouchEnd() {
    if (cameraDragState?.moved) {
      suppressCameraTapUntil = readNow() + 360
    }
    cameraDragState = null
  }

  watch(cameraSize, () => {
    clampCameraPosition()
  })

  return {
    cameraSizeClass,
    floatingCameraStyle,
    cameraSizeText,
    resetCameraPosition,
    cycleCameraSize,
    handleCameraTap,
    onCameraTouchStart,
    onCameraTouchMove,
    onCameraTouchEnd
  }
}
