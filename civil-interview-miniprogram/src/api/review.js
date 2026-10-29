import { request } from './request'
const call = (url, method, data) => request({ url: `/user/review-items${url}`, method, data, skipErrorHandler: true })
export const reviewApi = {
  list: params => call('', 'GET', params),
  update: body => call('', 'PUT', body),
  clear: scope => call('/clear', 'POST', { scope }),
  importItems: items => call('/import', 'POST', { items })
}
