/**
 * 这个接口文件负责考试创建、提交和完成接口封装；页面只调用这里的方法，避免到处拼 URL 和重复处理错误。
 *
 * @param 无；文件级模块依赖导出函数、组合式 API 或调用方传入上下文。
 * @return 导出可复用的端侧能力，具体返回值由各公共函数保持兼容。
 * @raises 不主动吞掉业务异常；请求失败、权限不足和运行时错误交由调用方或全局拦截器处理。
 */
import { http } from './index'
import { buildExamUploadFormData } from '@/utils/examSubmission'

export async function startExam(questionIds) {
  return http.post('/exam/start', { questionIds })
}

export async function uploadRecording(examId, questionId, blob) {
  const formData = buildExamUploadFormData({
    questionId,
    blob,
    filename: `recording_${Date.now()}.webm`
  })
  return http.post(`/exam/${examId}/upload`, formData, {
    headers: { 'Content-Type': 'multipart/form-data' },
    timeout: 60000
  })
}

export async function completeExam(examId) {
  return http.post(`/exam/${examId}/complete`)
}
