import { http } from './index'
const silent = { skipErrorHandler: true }
export const reviewApi = {
  list: params => http.get('/user/review-items', { ...silent, params }),
  update: body => http.put('/user/review-items', body, silent),
  clear: scope => http.post('/user/review-items/clear', { scope }, silent),
  importItems: items => http.post('/user/review-items/import', { items }, silent)
}
