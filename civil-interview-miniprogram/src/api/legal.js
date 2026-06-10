/**
 * 协议与隐私接口封装，集中读取服务条款、隐私政策和版本文案，方便审核材料同步。
 *
 * 登录页、个人中心和审核材料都使用同一份协议内容；这里避免小程序页面硬编码协议版本，
 * 也避免用户确认版本和实际展示内容不一致。
 *
 * @param config: 可选请求配置，常用于跳过全局错误提示。
 * @return Promise，解析服务条款、隐私政策和版本信息。
 * @raises Error: 文档接口不可用或返回结构异常会由 request 层抛出。
 */
import { request } from './request'

export function getLegalDocuments(config = {}) {
  return request({
    url: '/legal/documents',
    skipErrorHandler: true,
    ...config
  })
}
