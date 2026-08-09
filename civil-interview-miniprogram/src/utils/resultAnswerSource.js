/**
 * 判断小程序结果页是否可以复用 store 中的本地答案。
 *
 * 历史结果通过 examId 打开时，路由考试必须优先于当前 store，避免跨考试串答案。
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
