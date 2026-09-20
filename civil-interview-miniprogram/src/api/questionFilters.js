import { request } from './request'

// Metadata only. The server applies the same entitlement and exact matching as /questions.
export async function getQuestionFilterOptions(params = {}, options = {}) {
  const response = await request({ url: '/questions/filter-options', data: params, timeout: 12000, skipErrorHandler: true, signal: options.signal })
  if (!response?.options || ['year', 'subcategory', 'subcategory2'].some(key => !Array.isArray(response.options[key]) || response.options[key].some(value => typeof value !== 'string'))) {
    throw new Error('筛选选项格式异常，请重试')
  }
  return response
}
