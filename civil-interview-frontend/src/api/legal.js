import { http } from './index'

export function getLegalDocuments() {
  return http.get('/legal/documents', {
    skipErrorHandler: true
  })
}
