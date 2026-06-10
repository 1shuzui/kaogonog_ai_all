/**
 * PC 展示格式化工具用于把后端返回的秒数、分数、日期和文件大小转成稳定中文界面文案。
 *
 * 这些函数宁可返回原值或空值，也不要在格式化层推断业务含义；例如无效日期不能被包装成“今天”，避免误导历史记录和订单时间。
 *
 * @param 无；导出函数接收待展示的原始值。
 * @return 导出时间、分数、日期和文件大小格式化函数，供 PC 页面和组件复用。
 * @raises 参数异常通常返回兜底值；需要阻断流程的错误交由调用方处理。
 */
/**
 * 格式化秒数为 mm:ss
 */
export function formatTime(seconds) {
  const m = Math.floor(seconds / 60)
  const s = seconds % 60
  return `${String(m).padStart(2, '0')}:${String(s).padStart(2, '0')}`
}

/**
 * 格式化分数
 */
export function formatScore(score, maxScore) {
  return `${score}/${maxScore}`
}

/**
 * 格式化日期
 */
export function formatDate(dateStr) {
  if (!dateStr) return ''
  const d = new Date(dateStr)
  if (Number.isNaN(d.getTime())) return String(dateStr)
  const y = d.getFullYear()
  const m = String(d.getMonth() + 1).padStart(2, '0')
  const day = String(d.getDate()).padStart(2, '0')
  const h = String(d.getHours()).padStart(2, '0')
  const min = String(d.getMinutes()).padStart(2, '0')
  return `${y}-${m}-${day} ${h}:${min}`
}

/**
 * 格式化文件大小
 */
export function formatFileSize(bytes) {
  if (bytes < 1024) return bytes + ' B'
  if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(1) + ' KB'
  return (bytes / (1024 * 1024)).toFixed(1) + ' MB'
}
