import test from 'node:test'
import assert from 'node:assert/strict'
import { getQuestionScorePair as webPair } from '../src/utils/scorePresentation.js'
import { getQuestionScorePair as miniPair } from '../../civil-interview-miniprogram/src/utils/scorePresentation.js'

for (const [client, getPair] of [['web', webPair], ['miniprogram', miniPair]]) {
  test(`${client}: includes appearance exactly once in the effective score`, () => {
    const result = { totalScore: 28.25, maxScore: 36, contentScore: 23.25,
      appearanceScore: 5, questionScore: 23.25, questionMaxScore: 36 }
    assert.deepEqual(getPair(result, 31), { score: 28.25, maxScore: 36 })
    assert.deepEqual(getPair({ ...result, totalScore: 0, contentScore: 0, appearanceScore: 0 }),
      { score: 0, maxScore: 36 })
  })
  test(`${client}: keeps legacy question point conversion and missing-data fallback`, () => {
    assert.deepEqual(getPair({ totalScore: 80, maxScore: 100, questionScore: 24, questionMaxScore: 30 }),
      { score: 24, maxScore: 30 })
    assert.deepEqual(getPair({ totalScore: 24 }, 30), { score: 24, maxScore: 30 })
    assert.deepEqual(getPair({ totalScore: 80, maxScore: 100 }), { score: 80, maxScore: 100 })
  })
}
