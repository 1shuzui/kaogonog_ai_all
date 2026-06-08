/**
 * 这个接口文件负责历史记录和成绩趋势接口封装；页面只调用这里的方法，避免到处拼 URL 和重复处理错误。
 *
 * @param 无；文件级模块依赖导出函数、组合式 API 或调用方传入上下文。
 * @return 导出可复用的端侧能力，具体返回值由各公共函数保持兼容。
 * @raises 不主动吞掉业务异常；请求失败、权限不足和运行时错误交由调用方或全局拦截器处理。
 */
import { request } from './request'

export function getHistoryList(params = {}) {
  return request({
    url: '/history',
    data: params
  })
}

export function getHistoryDetail(examId) {
  return request({
    url: `/history/${examId}`
  })
}

export function getHistoryTrend(days = 30) {
  return request({
    url: '/history/trend',
    data: { days }
  })
}

export function getHistoryStats() {
  return request({
    url: '/history/stats'
  })
}
