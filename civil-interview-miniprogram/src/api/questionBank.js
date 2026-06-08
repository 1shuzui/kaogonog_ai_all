/**
 * 这个接口文件负责题库查询、导入和编辑接口封装；页面只调用这里的方法，避免到处拼 URL 和重复处理错误。
 *
 * @param 无；文件级模块依赖导出函数、组合式 API 或调用方传入上下文。
 * @return 导出可复用的端侧能力，具体返回值由各公共函数保持兼容。
 * @raises 不主动吞掉业务异常；请求失败、权限不足和运行时错误交由调用方或全局拦截器处理。
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
