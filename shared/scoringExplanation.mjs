export const ABILITY_WEIGHT_NOTE = '能力维度采用内容百分制：综合分析 20、实务落地 20、应急应变 15、行政思维 15、逻辑结构 15、语言表达 15。能力条用于说明内容表现，不再加到题目总分中。'

export function scoringExplanation(result = {}) {
  const notes = [ABILITY_WEIGHT_NOTE]
  const hasAppearance = result.contentScore != null && result.appearanceScore != null
  if (hasAppearance) {
    const contentMax = result.contentMaxScore ?? (Number(result.maxScore) - Number(result.appearanceScoreMax || 0))
    notes.push(`本题内容分 ${result.contentScore} / ${contentMax}，仪态分 ${result.appearanceScore} / ${result.appearanceScoreMax ?? 0}，当前有效总分 ${result.totalScore} / ${result.maxScore}。`)
    notes.push(result.appearanceScoreSource === 'actual'
      ? '仪态分来源为实际评估，已替换默认仪态分。'
      : '当前仪态分来自题源或规则默认值，尚未完成实际仪态评估。录像用于回放，不表示已按画面完成仪态打分。')
    if (result.appearanceScoreScope === 'suite') notes.push('本套仪态分属于整套考试，汇总时只计一次；逐题展示的仪态分不能直接相加。')
  } else {
    notes.push('本题按题源规定的内容满分展示；不同满分的练习在历史总评中按有效得分率换算为百分制。')
  }
  notes.push('评分依据本题采分点、题库参考答案和实际作答。AI 结果用于训练参考，不代表官方考试成绩。')
  return notes
}
