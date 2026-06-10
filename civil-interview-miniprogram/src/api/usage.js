/**
 * 用量上报接口封装，用于扣减时长和记录答题消耗，避免页面自行修改权益余额。
 *
 * 小程序端只上报本次练习消耗，真实扣量、每日限额和人工权益优先级由后端完成；
 * 上报失败不应由页面擅自扣本地余额，避免刷新后和服务器不一致。
 *
 * @param data: 考试 ID、题目 ID、消耗秒数和练习类型。
 * @return Promise，解析后端扣量和最新权益快照。
 * @raises Error: 未登录、权益不足、用量越界或接口失败会由 request 层抛出。
 */
import { request } from './request'

export function reportUsage(data) {
  return request({
    url: '/usage/report',
    method: 'POST',
    data,
    skipErrorHandler: true
  })
}
