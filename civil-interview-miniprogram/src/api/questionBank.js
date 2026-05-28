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
