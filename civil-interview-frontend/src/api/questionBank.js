import { http, USE_MOCK } from './index'
import { getMockQuestions, getMockQuestionById, getMockRandomQuestions } from './mock/questionBank'

export async function getQuestions(params) {
  if (USE_MOCK) return getMockQuestions(params)
  return http.get('/questions', { params })
}

export async function getQuestionById(id) {
  if (USE_MOCK) return getMockQuestionById(id)
  return http.get(`/questions/${id}`)
}

export async function createQuestion(data) {
  if (USE_MOCK) {
    return { ...data, id: `q_${Date.now()}` }
  }
  return http.post('/questions', data)
}

export async function updateQuestion(id, data) {
  if (USE_MOCK) return { ...data, id }
  return http.put(`/questions/${id}`, data)
}

export async function deleteQuestion(id) {
  if (USE_MOCK) return { success: true }
  return http.delete(`/questions/${id}`)
}

export async function importQuestions(payload) {
  if (USE_MOCK) {
    const total = Array.isArray(payload) ? payload.length : 10
    return { imported: total, failed: 0 }
  }
  const formData = new FormData()
  if (Array.isArray(payload)) {
    const jsonBlob = new Blob([JSON.stringify(payload)], { type: 'application/json' })
    formData.append('file', jsonBlob, `questions_${Date.now()}.json`)
  } else {
    formData.append('file', payload)
  }
  return http.post('/questions/import', formData, {
    headers: { 'Content-Type': 'multipart/form-data' }
  })
}

export async function getRandomQuestions(params) {
  if (USE_MOCK) return getMockRandomQuestions(params)
  return http.get('/questions/random', { params })
}
