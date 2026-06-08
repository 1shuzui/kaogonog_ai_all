/**
 * 这个接口文件负责题库查询、导入和编辑接口封装；页面只调用这里的方法，避免到处拼 URL 和重复处理错误。
 *
 * @param 无；文件级模块依赖导出函数、组合式 API 或调用方传入上下文。
 * @return 导出可复用的端侧能力，具体返回值由各公共函数保持兼容。
 * @raises 不主动吞掉业务异常；请求失败、权限不足和运行时错误交由调用方或全局拦截器处理。
 */
import { http } from './index'

export async function getQuestions(params) {
  return http.get('/questions', { params })
}

export async function getQuestionById(id) {
  return http.get(`/questions/${id}`)
}

export async function createQuestion(data) {
  return http.post('/questions', data)
}

export async function updateQuestion(id, data) {
  return http.put(`/questions/${id}`, data)
}

export async function deleteQuestion(id) {
  return http.delete(`/questions/${id}`)
}

export async function importQuestions(file) {
  const formData = new FormData()
  formData.append('file', file)
  return http.post('/questions/import', formData, {
    headers: { 'Content-Type': 'multipart/form-data' }
  })
}

export async function importDocx(file, province) {
  const formData = new FormData()
  formData.append('file', file)
  return http.post('/questions/import/docx', formData, {
    params: { province },
    headers: { 'Content-Type': 'multipart/form-data' }
  })
}

export async function getRandomQuestions(params) {
  return http.get('/questions/random', { params })
}
