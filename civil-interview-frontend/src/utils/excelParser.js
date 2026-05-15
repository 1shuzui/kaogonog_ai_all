/**
 * 解析JSON文件为题库数据
 */
export async function parseJsonFile(file) {
  return new Promise((resolve, reject) => {
    const reader = new FileReader()
    reader.onload = (e) => {
      try {
        const data = JSON.parse(e.target.result)
        const questions = Array.isArray(data)
          ? data
          : (Array.isArray(data.questions) ? data.questions : (data?.stem || data?.question ? [data] : []))
        resolve(questions)
      } catch (err) {
        reject(new Error('JSON解析失败: ' + err.message))
      }
    }
    reader.onerror = () => reject(new Error('文件读取失败'))
    reader.readAsText(file)
  })
}
