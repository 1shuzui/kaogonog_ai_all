/**
 * 协议与隐私接口封装，集中读取服务条款、隐私政策和版本文案，方便审核材料同步。
 *
 * 审核材料、登录页勾选版本和用户协议确认都依赖这里；协议内容不应在多个页面硬编码，
 * 否则版本更新后容易出现“用户看到的”和“后端记录的”不一致。
 *
 * @param config: 可选请求配置，常用于跳过全局错误提示。
 * @return Promise，解析后端返回的协议、隐私政策和版本信息。
 * @raises AxiosError: 文档接口不可用或返回结构异常会由调用页面处理。
 */
import { http } from './index'

export function getLegalDocuments() {
  return http.get('/legal/documents', {
    skipErrorHandler: true
  })
}
