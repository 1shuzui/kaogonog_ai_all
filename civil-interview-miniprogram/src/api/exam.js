/**
 * 小程序考试接口封装，承接开考、录音上传、提交作答、全真模拟套题和考场状态请求。
 *
 * 考场页只负责录音、权限和交互状态；题目顺序、用量扣减、分数展示和评分结果都以后端确认为准。
 * 录音开始前由页面确认麦克风权限，上传字段在这里保持和 PC 端同一后端契约。
 *
 * @param questionIds: 本次考试锁定的题目 ID 顺序。
 * @param filePath: 小程序录音或录像的本地临时文件路径。
 * @return Promise，解析开考、上传、提交答案或全真模拟套题结果。
 * @raises Error: 未登录、权益不足、上传失败、考试不存在或接口异常会由 request 层抛出。
 */
import { request, uploadFile } from './request'

export function startExam(questionIds = []) {
  return request({
    url: '/exam/start',
    method: 'POST',
    data: { questionIds }
  })
}

export function uploadRecording(examId, questionId, filePath, options = {}) {
  const mediaType = options.mediaType || 'audio'
  return uploadFile({
    url: `/exam/${examId}/upload`,
    filePath,
    name: 'recording',
    formData: {
      questionId,
      mediaType,
      source: options.source || `miniapp_${mediaType}_recording`
    },
    timeout: mediaType === 'video' ? 120000 : 60000
  })
}

export function completeExam(examId) {
  return request({
    url: `/exam/${examId}/complete`,
    method: 'POST'
  })
}
