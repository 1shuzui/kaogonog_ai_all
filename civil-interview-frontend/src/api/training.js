import { http } from './index'

export async function generateTrainingQuestions(data, sourceMode = 'local') {
  const result = await http.post('/training/generate', {
    ...data,
    sourceMode
  })
  return Array.isArray(result) ? result : (result?.questions || [])
}
