import test from 'node:test'
import assert from 'node:assert/strict'
import vm from 'node:vm'
import { readFileSync } from 'node:fs'
import { createCancellation } from '../src/utils/cancellation.mjs'
const source = readFileSync(new URL('../src/utils/useQuestionFilters.js', import.meta.url), 'utf8').replace(/^import .*$/gm, '').replace('export function', 'function')
function fixture() {
  const jobs = [], disposals = []
  const context = vm.createContext({ ref:value=>({value}), onBeforeUnmount:fn=>disposals.push(fn), createCancellation,
    getQuestionFilterOptions:(params,options)=>new Promise((resolve,reject)=>jobs.push({params,signal:options.signal,resolve,reject})) })
  const filters = vm.runInContext(`${source}\nuseQuestionFilters()`, context)
  return {filters,jobs,dispose:()=>disposals.forEach(fn=>fn())}
}
const response = years => ({options:{year:years,subcategory:[],subcategory2:[]},questionCount:years.length})
test('metadata excludes its own selected year and ignores old responses and finally', async () => {
  const {filters,jobs} = fixture()
  const old = filters.refresh({province:'jiangsu',year:'2024'})
  const latest = filters.refresh({province:'shandong',year:'2025'})
  assert.equal(jobs[0].params.year, '')
  assert.equal(jobs[0].signal.aborted, true)
  jobs[0].resolve(response(['2024'])); await old
  assert.equal(filters.loading.value,true)
  assert.equal(filters.options.value.year.length,0)
  jobs[1].resolve(response(['2026'])); await latest
  assert.deepEqual(filters.options.value.year,['2026'])
  assert.equal(filters.loading.value,false)
})
test('metadata disabled access clears data and late failure cannot leak an old scope', async () => {
  const {filters,jobs,dispose} = fixture()
  const pending=filters.refresh({})
  await filters.refresh({},false)
  jobs[0].reject(new Error('old')); await pending
  assert.equal(filters.error.value,'')
  assert.equal(filters.loading.value,false)
  assert.equal(jobs.length,1)
  dispose()
})
test('metadata failure is retryable and no fake years are inserted', async () => {
  const {filters,jobs,dispose}=fixture()
  const first=filters.refresh({}); jobs[0].reject(new Error('offline')); await first
  assert.equal(filters.error.value,'offline')
  assert.equal(filters.options.value.year.length,0)
  const retry=filters.refresh({}); jobs[1].resolve(response(['2016','2026'])); await retry
  assert.equal(filters.error.value,'')
  assert.equal(filters.options.value.year.length,2)
  const leaving=filters.refresh({}); dispose(); jobs[2].resolve(response(['1999'])); await leaving
  assert.equal(filters.options.value.year.length,0)
})
