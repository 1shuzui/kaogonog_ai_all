/**
 * 题库接口封装，集中管理筛选、详情、导入和管理员维护请求，避免题库页面散落参数转换。
 *
 * 题库筛选必须保持真实考试体系、地区、岗位、面试形式和题型维度分离；
 * 小程序管理员维护入口也走这组接口，避免移动端和 PC 后台出现两套分类写法。
 *
 * @param params: 题库列表、详情、导入或管理员维护所需的筛选和表单数据。
 * @return Promise，解析题目列表、题目详情、导入结果或管理操作结果。
 * @raises Error: 未登录、非管理员、题目不存在、导入失败或接口异常会由 request 层抛出。
 */
import { request, uploadFile } from './request'

export function getQuestions(params = {}) {
  return request({
    url: '/questions',
    data: params
  })
}

export function getQuestionById(id) {
  return request({
    url: `/questions/${id}`
  })
}

export function getRandomQuestions(params = {}) {
  return request({
    url: '/questions/random',
    data: params
  })
}

export function createQuestion(data) {
  return request({
    url: '/questions',
    method: 'POST',
    data
  })
}

export function updateQuestion(id, data) {
  return request({
    url: `/questions/${encodeURIComponent(id)}`,
    method: 'PUT',
    data
  })
}

export function deleteQuestion(id) {
  return request({
    url: `/questions/${encodeURIComponent(id)}`,
    method: 'DELETE'
  })
}

export function importQuestions(filePath) {
  return uploadFile({
    url: '/questions/import',
    filePath,
    name: 'file'
  })
}

export function importDocx(filePath, province) {
  return uploadFile({
    url: '/questions/import/docx',
    filePath,
    name: 'file',
    formData: { province }
  })
}
