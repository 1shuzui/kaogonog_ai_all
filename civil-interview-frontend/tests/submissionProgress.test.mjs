import test from 'node:test'
import assert from 'node:assert/strict'
import { submissionProgress as pc } from '../src/utils/submissionProgress.js'
import { submissionProgress as mini } from '../../civil-interview-miniprogram/src/utils/submissionProgress.js'

test('两端进度仅反映已完成阶段，失败指向可重试步骤，不伪造百分比', () => {
  const cases = [
    [{ processingStatus: 'queued' }, ['waiting', 'waiting', 'waiting']],
    [{ processingStatus: 'transcribing' }, ['done', 'active', 'waiting']],
    [{ processingStatus: 'scoring' }, ['done', 'done', 'active']],
    [{ processingStatus: 'failed' }, ['failed', 'waiting', 'waiting']],
    [{ processingStatus: 'failed', mediaUploaded: true }, ['done', 'failed', 'waiting']],
    [{ processingStatus: 'failed', transcript: '真实原文' }, ['done', 'done', 'failed']],
    [{ processingStatus: 'completed' }, ['done', 'done', 'done']],
  ]
  for (const progress of [pc, mini]) {
    for (const [answer, expected] of cases) assert.deepEqual(progress(answer).map((step) => step.state), expected)
  }
})
