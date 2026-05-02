import { request } from './request'

export async function generateTrainingQuestions(data) {
  const response = await request({
    url: '/training/generate',
    method: 'POST',
    data
  })
  return Array.isArray(response?.questions) ? response.questions : response
}
