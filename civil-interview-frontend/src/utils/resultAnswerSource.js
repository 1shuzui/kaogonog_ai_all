/**
 * 判断结果页是否可以复用 store 中的本地答案。
 *
 * 结果页既可能从刚刚完成的考试进入，也可能通过历史记录的 examId 进入。
 * 当两者考试编号不一致时，必须回源历史详情，不能把当前考试的答案展示到历史考试页面。
 *
 * @param requestedExamId: 路由或分享链接指定的考试编号。
 * @param localExamId: store 当前保存的考试编号。
 * @param answers: store 中的本地答案列表。
 * @return: 只有答案存在且考试上下文一致时返回 true。
 * @raises: 不主动抛出异常；无效答案列表返回 false。
 */
export function canUseLocalAnswers(requestedExamId = '', localExamId = '', answers = []) {
  if (!Array.isArray(answers) || answers.length === 0) return false

  const requested = String(requestedExamId || '').trim()
  const local = String(localExamId || '').trim()
  if (!requested) return true
  return Boolean(local && local === requested)
}
