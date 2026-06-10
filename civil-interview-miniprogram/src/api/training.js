/**
 * 专项训练接口封装，按题型训练入口复用同一请求层，不把训练分类混成能力维度。
 *
 * `dimension` 在这里表示题型训练分类，不表示行政思维、实务落地这类评分能力维度；
 * 页面只传筛选条件，题目是否可用和权益是否足够由后端判断。
 *
 * @param data: 题型分类、题量、来源模式和可选地区/考试体系筛选。
 * @return Promise，成功时返回可直接进入练习的题目数组或后端兼容结构。
 * @raises Error: 未登录、权益不足、题库无匹配或接口失败会由 request 层抛出。
 */
import { request } from './request'

export async function generateTrainingQuestions(data) {
  const response = await request({
    url: '/training/generate',
    method: 'POST',
    data
  })
  return Array.isArray(response?.questions) ? response.questions : response
}
