// Derive visual stages from confirmed work; never invent a time-based percentage.
export function submissionProgress(answer) {
  const status = answer.processingStatus
  const failedStage = answer.transcript ? 2 : answer.mediaUploaded ? 1 : 0
  const current = status === 'failed'
    ? failedStage
    : { queued: -1, uploading: 0, transcribing: 1, scoring: 2, completed: 3 }[status] ?? -1
  return ['上传', '转写', '点评'].map((label, index) => ({
    label,
    state: index < current ? 'done' : index === current ? (status === 'failed' ? 'failed' : 'active') : 'waiting',
  }))
}
