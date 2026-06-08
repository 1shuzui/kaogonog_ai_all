/**
 * 这个文件封装小程序录音/录像上传；开始录音前的权限确认和文件字段统一处理，避免评分接口收不到媒体。
 *
 * @param 无；文件级模块依赖导出函数、组合式 API 或调用方传入上下文。
 * @return 导出可复用的端侧能力，具体返回值由各公共函数保持兼容。
 * @raises 不主动吞掉业务异常；请求失败、权限不足和运行时错误交由调用方或全局拦截器处理。
 */
const VIDEO_COMPRESS_THRESHOLD_BYTES = 1800 * 1024

function getFileSize(filePath) {
  if (!filePath || typeof uni.getFileInfo !== 'function') return Promise.resolve(0)
  return new Promise((resolve) => {
    uni.getFileInfo({
      filePath,
      success(res) {
        resolve(Number(res.size || 0))
      },
      fail() {
        resolve(0)
      }
    })
  })
}

function compressVideo(filePath) {
  if (!filePath || typeof uni.compressVideo !== 'function') return Promise.resolve(filePath)
  return new Promise((resolve) => {
    uni.compressVideo({
      src: filePath,
      quality: 'low',
      bitrate: 512,
      fps: 15,
      resolution: 0.6,
      success(res) {
        resolve(res.tempFilePath || filePath)
      },
      fail() {
        resolve(filePath)
      }
    })
  })
}

export async function prepareMediaForUpload(filePath, mediaType = 'audio') {
  const normalizedType = mediaType === 'video' ? 'video' : 'audio'
  const originalSize = await getFileSize(filePath)

  if (normalizedType !== 'video' || !filePath) {
    return {
      filePath,
      mediaType: normalizedType,
      originalFilePath: filePath,
      originalSize,
      compressedSize: originalSize,
      compressed: false
    }
  }

  if (originalSize > 0 && originalSize <= VIDEO_COMPRESS_THRESHOLD_BYTES) {
    return {
      filePath,
      mediaType: normalizedType,
      originalFilePath: filePath,
      originalSize,
      compressedSize: originalSize,
      compressed: false
    }
  }

  const compressedPath = await compressVideo(filePath)
  const compressedSize = await getFileSize(compressedPath)
  return {
    filePath: compressedPath || filePath,
    mediaType: normalizedType,
    originalFilePath: filePath,
    originalSize,
    compressedSize: compressedSize || originalSize,
    compressed: !!compressedPath && compressedPath !== filePath
  }
}
