/** Display effective totals when appearance is separate; retain legacy question scaling. */
export function getQuestionScorePair(scoring = {}, assignedScore = 0) {
  const number = (value, fallback = 0) => Number.isFinite(Number(value)) ? Number(value) : fallback
  const hasAppearance = scoring.contentScore != null && scoring.appearanceScore != null
  const maxScore = hasAppearance
    ? number(scoring.maxScore) || number(scoring.questionMaxScore) || 100
    : number(scoring.questionMaxScore) || number(assignedScore) || number(scoring.maxScore) || 100
  const score = hasAppearance
    ? number(scoring.totalScore)
    : number(scoring.questionScore ?? scoring.totalScore)
  return { score, maxScore: maxScore > 0 ? maxScore : 100 }
}
