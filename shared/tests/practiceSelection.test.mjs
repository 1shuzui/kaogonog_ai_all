import test from 'node:test'
import assert from 'node:assert/strict'
import { readPracticeSelection, loadSelectedQuestions, practiceModeFor, practiceQuery, miniPracticeUrl } from '../practiceSelection.mjs'

test('explicit single question takes priority over stale list and generated cache', () => {
  assert.deepEqual(readPracticeSelection({ questionId: 'chosen', questionIds: 'old-1,old-2' }, [{id:'cached'}]).ids, ['chosen'])
})
test('ordered group survives route round trip with complete filter snapshot', async () => {
  const filters = { province: 'jiangsu', year: '2024,2023', examCategory: '事业单位考试', subcategory: '综合岗', subcategory2: 'A 类', dimension: 'analysis', position:'comprehensive' }
  const options = { source:'targeted', questionIds:['q3','q1','q2'], filters }
  const url = miniPracticeUrl(options)
  const selection = readPracticeSelection(Object.fromEntries(new URL(`https://local${url}`).searchParams))
  assert.deepEqual(selection, {ids:options.questionIds, filters})
  const questions = await loadSelectedQuestions(selection.ids, async id => ({id}))
  assert.deepEqual(questions.map(q=>q.id), options.questionIds)
  assert.deepEqual(readPracticeSelection(practiceQuery(options)), selection)
})
test('failure or mismatched identity rejects entire selected group without replacement', async () => {
  await assert.rejects(loadSelectedQuestions(['q1','q2'], async id => {if(id==='q2') throw new Error('offline');return{id}}), /offline/)
  await assert.rejects(loadSelectedQuestions(['q1'], async () => ({id:'q2'})), /指定题目/)
})
test('invalid or oversized lists and malformed snapshots are visible failures', () => {
  for(const questionIds of ['q1,,q2','q1,q1',Array.from({length:11},(_,i)=>`q${i}`).join(',')]) assert.throws(()=>readPracticeSelection({questionIds}))
  assert.throws(()=>readPracticeSelection({filterSnapshot:'{broken'}), /筛选/)
})
test('practice mode labels come from entry intent, including specific question entries', () => {
  assert.equal(practiceModeFor('targeted'), 'targeted')
  assert.equal(practiceModeFor('training'), 'training')
  assert.equal(practiceModeFor('bank'), 'free')
  assert.equal(practiceModeFor('targeted','fullExam'), 'fullExam')
  assert.equal(practiceModeFor('training','free',true), 'trial')
})
