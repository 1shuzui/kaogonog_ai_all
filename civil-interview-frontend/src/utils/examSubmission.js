/**
 * PC 考试提交工具统一构造录音上传表单，避免不同考场页使用不同字段名导致后端无法转写或评分。
 *
 * 它只处理“是否有真实媒体内容”和 FormData 字段，不负责 ASR 纠错、评分或权益扣减；这些都必须留在后端流程里。
 *
 * @param 无；导出函数接收题目 id、录音 Blob 和文件名。
 * @return 导出媒体内容判断和考试上传 FormData 构造函数。
 * @raises 参数异常通常返回兜底值；需要阻断流程的错误交由调用方处理。
 */
export function hasRecordingContent(blob) {
  return blob instanceof Blob && blob.size > 0
}

export function buildExamUploadFormData({ questionId, blob, filename }) {
  const formData = new FormData()
  formData.append('questionId', String(questionId || ''))
  formData.append('recording', blob, filename || `recording_${Date.now()}.webm`)
  return formData
}
