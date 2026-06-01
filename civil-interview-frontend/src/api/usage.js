import { http } from './index'

export async function reportUsage(data) {
  return http.post('/usage/report', data)
}
