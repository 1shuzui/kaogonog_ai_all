/** A pending transcript/media record is not a completed zero-point assessment. */
export function hasFinalScore(result) {
  const score = result?.totalScore ?? result?.score
  return score !== undefined && score !== null && score !== '' && Number.isFinite(Number(score))
}
