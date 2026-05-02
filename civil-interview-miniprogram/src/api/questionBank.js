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

export function importQuestions(filePath) {
  return uploadFile({
    url: '/questions/import',
    filePath,
    name: 'file'
  })
}
