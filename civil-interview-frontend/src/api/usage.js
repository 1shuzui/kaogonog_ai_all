/**
 * 用量上报接口封装，用于扣减时长和记录答题消耗，避免页面自行修改权益余额。
 *
 * 端侧只上报本次练习消耗，真实扣减、每日限额和人工权益优先级由后端决定；
 * 这样可以避免刷新页面、离线恢复或重复提交时把余额算错。
 *
 * @param data: 考试 ID、题目 ID、消耗秒数和练习类型。
 * @return Promise，解析后端扣量和最新权益快照。
 * @raises AxiosError: 未登录、权益不足、用量越界或接口失败会抛给调用页面。
 */
import { http } from './index'

export async function reportUsage(data) {
  return http.post('/usage/report', data)
}
