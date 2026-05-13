import { request } from './request'

export function getLegalDocuments(config = {}) {
  return request({
    url: '/legal/documents',
    skipErrorHandler: true,
    ...config
  })
}
