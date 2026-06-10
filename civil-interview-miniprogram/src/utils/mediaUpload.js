/**
 * 小程序媒体上传工具在提交前整理录音或视频文件，尤其是压缩较大的视频，避免移动网络下上传失败。
 *
 * 这里不做 ASR、VAD 或评分判断，只保证传给后端的文件路径、类型和大小信息稳定；语音切分与转写质量优化留在后端管线。
 *
 * @param 无；导出函数接收小程序临时文件路径和媒体类型。
 * @return 导出上传前媒体准备函数，返回原始/压缩路径和大小信息。
 * @raises 参数异常通常返回兜底值；需要阻断流程的错误交由调用方处理。
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
