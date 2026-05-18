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

export async function getRandomQuestions(params) {
  return http.get('/questions/random', { params })
}
