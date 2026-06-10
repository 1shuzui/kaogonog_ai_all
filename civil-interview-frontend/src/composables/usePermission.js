/**
 * 权限组合函数在进入考场或开始录音前探测摄像头和麦克风，减少用户答题后才发现无法提交的情况。
 *
 * 它只处理浏览器设备权限和提示，不记录用户隐私授权，也不替代小程序侧的麦克风确认流程。
 *
 * @param 无；组合函数运行时接收是否保留媒体流等检查选项。
 * @return 导出摄像头/麦克风可用状态、错误文案和检查方法。
 * @raises 浏览器权限、网络和运行时异常按函数内部策略提示或交由调用方处理。
 */
import { ref } from 'vue'

export function usePermission() {
  const cameraReady = ref(false)
  const micReady = ref(false)
  const error = ref('')
  const checking = ref(false)

  async function checkCamera() {
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ video: true })
      stream.getTracks().forEach(t => t.stop())
      cameraReady.value = true
      return true
    } catch (e) {
      cameraReady.value = false
      error.value = '摄像头访问失败: ' + (e.message || '请检查权限设置')
      return false
    }
  }

  async function checkMicrophone() {
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true })
      stream.getTracks().forEach(t => t.stop())
      micReady.value = true
      return true
    } catch (e) {
      micReady.value = false
      error.value = '麦克风访问失败: ' + (e.message || '请检查权限设置')
      return false
    }
  }

  // 同时请求摄像头+麦克风权限，避免分开请求时设备冲突
  async function checkBoth(opts = {}) {
    checking.value = true
    error.value = ''
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ video: true, audio: true })
      if (opts.keepStream) {
        cameraReady.value = true
        micReady.value = true
        checking.value = false
        return stream
      }
      stream.getTracks().forEach(t => t.stop())
      cameraReady.value = true
      micReady.value = true
      checking.value = false
      return true
    } catch {
      // 同时请求失败，尝试分别检测以确定具体哪个设备有问题
      await checkCamera()
      // 加延迟避免设备占用冲突
      await new Promise(r => setTimeout(r, 500))
      await checkMicrophone()
      checking.value = false

      if (!cameraReady.value && !micReady.value) {
        error.value = '摄像头和麦克风均无法访问，请检查设备连接和浏览器权限设置'
      } else if (!cameraReady.value && micReady.value) {
        // 摄像头不可用但麦克风正常，提示用户可以继续
        error.value = '摄像头无法访问，可尝试仅使用麦克风模式'
      } else if (!micReady.value) {
        error.value = '麦克风无法访问，请检查设备是否被其他程序占用'
      }
      return cameraReady.value && micReady.value
    }
  }

  // 仅检测麦克风（跳过摄像头模式）
  async function checkMicOnly() {
    checking.value = true
    error.value = ''
    cameraReady.value = false
    await new Promise(r => setTimeout(r, 300))
    const ok = await checkMicrophone()
    checking.value = false
    return ok
  }

  return {
    cameraReady,
    micReady,
    error,
    checking,
    checkCamera,
    checkMicrophone,
    checkBoth,
    checkMicOnly
  }
}
