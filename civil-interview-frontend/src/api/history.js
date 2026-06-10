/**
 * 历史记录接口封装，用于练习记录、成绩趋势和错题回看，避免页面重复处理分页参数。
 *
 * 历史数据是个人能力趋势、错题本和首页概览的共同来源，必须按后端返回的记录为准；
 * 前端不能用当前题库筛选结果反推出历史成绩。
 *
 * @param params: 分页、时间范围、题型或考试来源筛选参数。
 * @return Promise，解析历史列表、详情、趋势或维度统计结果。
 * @raises AxiosError: 未登录、记录不存在或分页参数错误会由请求层抛给调用页面处理。
 */
import { http } from './index'

export async function getHistoryList(params) {
  return http.get('/history', { params })
}

export async function getHistoryDetail(examId) {
  return http.get(`/history/${examId}`)
}

export async function getHistoryTrend(days = 30) {
  return http.get('/history/trend', { params: { days } })
}

export async function getHistoryStats() {
  return http.get('/history/stats')
}
