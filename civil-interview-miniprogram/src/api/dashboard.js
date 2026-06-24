/**
 * 小程序活跃心跳 API。
 *
 * 该接口只在用户已登录且页面处于前台时静默上报真实活跃时长，不参与权益扣减。
 */
import { request } from './request'

export function reportDashboardHeartbeat(data) {
  return request({
    url: '/admin/dashboard/heartbeat',
    method: 'POST',
    data,
    timeout: 10000,
    skipErrorHandler: true
  })
}
