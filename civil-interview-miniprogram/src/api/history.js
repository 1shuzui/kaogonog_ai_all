/**
 * 历史记录接口封装，用于练习记录、成绩趋势和错题回看，避免页面重复处理分页参数。
 *
 * 历史数据属于账号能力，未登录用户只能浏览入口，不能请求个人趋势或错题详情；
 * 页面展示的薄弱维度和练习趋势都应来自这里，而不是从当前题库筛选结果临时拼出来。
 *
 * @param params: 分页、时间范围、题型或考试来源筛选参数。
 * @return Promise，解析历史列表、详情、趋势或维度统计结果。
 * @raises Error: 未登录、记录不存在、分页参数错误或接口失败会由 request 层抛出。
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
