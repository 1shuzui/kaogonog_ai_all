/**
 * 考试接口封装，承接抽题、提交、全真模拟和考场状态请求，保证 PC 考场只关心业务动作。
 *
 * 考场页不能自己推导题目顺序、上传字段或提交结果结构；这些都由后端考试服务确认，
 * 前端只负责把录音/录像和题目上下文交出去，再展示评分后的结果。
 *
 * @param questionIds: 本次考试锁定的题目 ID 顺序。
 * @param blob: PC 录制得到的音视频 Blob，由上传工具封装成 FormData。
 * @return Promise，解析开始考试、上传录音、提交答案或全真套题查询结果。
 * @raises AxiosError: 权益不足、考试不存在、上传失败或评分失败会由请求层抛给考场流程处理。
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
