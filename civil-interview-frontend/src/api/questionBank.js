/**
 * 题库接口封装，集中管理筛选、详情、导入和管理员维护请求，避免题库页面散落参数转换。
 *
 * 题库筛选必须使用真实考试体系、地区、岗位和题型维度这些独立字段；
 * 管理员导入和编辑也走同一组接口，避免用户侧和后台各自发明分类参数。
 *
 * @param params: 题库列表、详情、导入或管理员维护所需的筛选和表单数据。
 * @return Promise，解析题目列表、题目详情、导入结果或管理操作结果。
 * @raises AxiosError: 非管理员操作、题目不存在、导入校验失败或网络异常会抛给调用方。
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
