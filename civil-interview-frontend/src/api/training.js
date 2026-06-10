/**
 * 专项训练接口封装，按题型训练入口复用同一请求层，不把训练分类混成能力维度。
 *
 * `dimension` 在专项训练里表示题型分类，例如综合分析、组织管理、应急应变；
 * 行政思维、实务落地等能力维度只出现在评分和能力分析里。
 *
 * @param data: 题型分类、题量、来源模式和可选地区/考试体系筛选。
 * @return Promise，成功时返回可直接进入练习的题目数组。
 * @raises AxiosError: 未登录、权益不足、题库无匹配或接口失败会抛给调用页面。
 */
import { http } from './index'

export async function generateTrainingQuestions(data) {
  const response = await http.post('/training/generate', data)
  return Array.isArray(response?.questions) ? response.questions : []
}
