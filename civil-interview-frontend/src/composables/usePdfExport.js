/**
 * 这个组合式函数封装 `usePdfExport` 相关浏览器行为；页面复用它，是为了少碰底层 API 和生命周期细节。
 *
 * @param 无；文件级模块依赖导出函数、组合式 API 或调用方传入上下文。
 * @return 导出可复用的端侧能力，具体返回值由各公共函数保持兼容。
 * @raises 不主动吞掉业务异常；请求失败、权限不足和运行时错误交由调用方或全局拦截器处理。
 */
import { ref } from 'vue'
import { message } from 'ant-design-vue'
import { logger } from '@/utils/logger'

export function usePdfExport() {
  const exporting = ref(false)

  async function exportToPdf(element, fileName = '测评报告') {
    if (!element) {
      message.error('导出内容不存在')
      return
    }

    exporting.value = true
    try {
      const html2canvas = (await import('html2canvas')).default
      const { jsPDF } = await import('jspdf')

      const canvas = await html2canvas(element, {
        scale: 2,
        useCORS: true,
        backgroundColor: '#ffffff',
        ignoreElements: (el) => el.hasAttribute('data-html2canvas-ignore')
      })

      const imgData = canvas.toDataURL('image/jpeg', 0.95)
      const imgWidth = canvas.width
      const imgHeight = canvas.height

      // A4 dimensions in mm
      const a4Width = 210
      const a4Height = 297
      const margin = 10

      const contentWidth = a4Width - margin * 2
      const ratio = contentWidth / imgWidth
      const contentHeight = imgHeight * ratio

      const pdf = new jsPDF({
        orientation: contentHeight > a4Height ? 'p' : 'p',
        unit: 'mm',
        format: 'a4'
      })

      // Multi-page handling
      const pageContentHeight = a4Height - margin * 2
      let remainingHeight = contentHeight
      let position = 0

      while (remainingHeight > 0) {
        if (position > 0) {
          pdf.addPage()
        }

        pdf.addImage(
          imgData, 'JPEG',
          margin,
          margin - position,
          contentWidth,
          contentHeight
        )

        remainingHeight -= pageContentHeight
        position += pageContentHeight
      }

      pdf.save(`${fileName}.pdf`)
      // 释放 canvas 内存
      canvas.width = 0
      canvas.height = 0
      message.success('PDF导出成功')
    } catch (e) {
      logger.error('PDF export failed', {
        event: 'pdf.export.failed',
        file_name: fileName,
        error: e
      })
      message.error('PDF导出失败，请重试')
    } finally {
      exporting.value = false
    }
  }

  return { exporting, exportToPdf }
}
