import { ref } from 'vue'
import { message } from 'ant-design-vue'

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
      console.error('PDF export failed:', e)
      message.error('PDF导出失败，请重试')
    } finally {
      exporting.value = false
    }
  }

  return { exporting, exportToPdf }
}
