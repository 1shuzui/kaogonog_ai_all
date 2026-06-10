/**
 * 题库文件解析工具只在管理员导入前把 JSON 文件转成题目数组，真实字段校验和分类纠偏仍交给后端导入链路。
 *
 * 前端解析失败要尽早给出可读错误，避免管理员以为已经上传成功；解析成功也不代表题源分类、采分点或关键词已经合格。
 *
 * @param 无；导出函数接收浏览器 File 对象。
 * @return 导出导入文件解析函数，供题库导入页预处理上传内容。
 * @raises 参数异常通常返回兜底值；需要阻断流程的错误交由调用方处理。
 */
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
