import { http } from './index'

export async function getTrialStatus(config = {}) {
  return http.get('/trial/status', config)
}

export async function getTrialQuestion() {
  return http.get('/trial/question')
}

export async function completeTrial() {
  return http.post('/trial/complete')
}
