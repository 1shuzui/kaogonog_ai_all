import { http } from './index'

export async function generateTrainingQuestions(data) {
  const response = await http.post('/training/generate', data)
  return Array.isArray(response?.questions) ? response.questions : []
}
