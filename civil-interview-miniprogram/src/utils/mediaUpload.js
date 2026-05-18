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
