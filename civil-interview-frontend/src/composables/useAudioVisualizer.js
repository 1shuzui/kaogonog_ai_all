import { ref, onUnmounted } from 'vue'

export function useAudioVisualizer() {
  const canvasRef = ref(null)
  const isActive = ref(false)

  let audioContext = null
  let analyser = null
  let source = null
  let animationId = null

  function start(stream) {
    if (!canvasRef.value || !stream) return

    audioContext = new (window.AudioContext || window.webkitAudioContext)()
    analyser = audioContext.createAnalyser()
    analyser.fftSize = 256
    source = audioContext.createMediaStreamSource(stream)
    source.connect(analyser)

    isActive.value = true
    draw()
  }

  function draw() {
    if (!canvasRef.value || !analyser) return

    const canvas = canvasRef.value
    const ctx = canvas.getContext('2d')
    const bufferLength = analyser.frequencyBinCount
    const dataArray = new Uint8Array(bufferLength)

    const width = canvas.width
    const height = canvas.height

    function render() {
      animationId = requestAnimationFrame(render)
      analyser.getByteFrequencyData(dataArray)

      ctx.fillStyle = 'rgba(10, 22, 40, 0.3)'
      ctx.fillRect(0, 0, width, height)

      const barWidth = (width / bufferLength) * 1.5
      let x = 0

      for (let i = 0; i < bufferLength; i++) {
        const barHeight = (dataArray[i] / 255) * height * 0.8
        const gradient = ctx.createLinearGradient(0, height, 0, height - barHeight)
        gradient.addColorStop(0, 'rgba(43, 127, 212, 0.6)')
        gradient.addColorStop(1, 'rgba(27, 95, 170, 1)')

        ctx.fillStyle = gradient
        ctx.fillRect(x, height - barHeight, barWidth - 1, barHeight)
        x += barWidth + 1
      }
    }

    render()
  }

  function stop() {
    if (animationId) {
      cancelAnimationFrame(animationId)
      animationId = null
    }
    if (source) {
      source.disconnect()
      source = null
    }
    if (audioContext) {
      audioContext.close()
      audioContext = null
    }
    analyser = null
    isActive.value = false

    // 清空画布
    if (canvasRef.value) {
      const ctx = canvasRef.value.getContext('2d')
      ctx.clearRect(0, 0, canvasRef.value.width, canvasRef.value.height)
    }
  }

  onUnmounted(() => stop())

  return { canvasRef, isActive, start, stop }
}
