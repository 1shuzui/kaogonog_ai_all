import test from 'node:test'
import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import vm from 'node:vm'
import { setImmediate as settle } from 'node:timers/promises'
import * as Vue from 'vue'
import { parse, compileScript } from '@vue/compiler-sfc'
import * as contract from '../src/utils/targetedPerformance.mjs'
import { createCancellation } from '../src/utils/cancellation.mjs'
import { practiceFilterSummary } from '../../shared/practiceSelection.mjs'

const target = { province: 'jiangsu', year: ['2025', '2026'], positionType: '护理岗', prepTime: 0 }
const practice = contract.practiceContext(target, '应急应变', 'all')
function fixture(t, file) {
  const descriptor = parse(readFileSync(new URL('../src/' + file, import.meta.url), 'utf8')).descriptor
  const imports = compileScript(descriptor, { id: 'targeted-test' }).scriptSetupAst.filter(node => node.type === 'ImportDeclaration')
  const source = [...imports].reverse().reduce((text, node) => text.slice(0, node.start) + text.slice(node.end), descriptor.scriptSetup.content)
  const user = Vue.reactive({ token: 'alice' }), pending = [], events = [], loads = []
  const scope = Vue.effectScope()
  t.after(() => scope.stop())
  const request = body => new Promise((resolve, reject) => pending.push({ body: JSON.parse(JSON.stringify(body)), resolve, reject }))
  const sandbox = vm.createContext({ ...Vue, ...contract, console, createCancellation, practiceFilterSummary,
    TOKEN_STORAGE_KEY: 'token', PROVINCES: [], uni: {getStorageSync:()=>user.token},
    usePageMotion:()=>({}), useUserStore:()=>user, useTargetedPerformanceStore:()=>({setScope(){}}), requireLogin:()=>true,
    defineProps:()=>({context:practice,fixedIds:[],disabled:false}), defineEmits:()=>((name, value)=>events.push({name,value})),
    onMounted(){}, onLoad:fn=>loads.push(fn), onShow(){}, onHide(){}, onUnload(){},
    selectTargetedPractice:request, getPerformanceAnswers:request
  })
  const names = file.startsWith('pages') ? 'load, records, report, total, loading' : 'refresh, changeMode, selection, error, loading'
  const page = scope.run(() => vm.runInContext(source + `\n({${names}})`, sandbox))
  for (const fn of loads) fn({target:JSON.stringify(target), questionType:'应急应变',period:'all'})
  return { user, pending, events, page }
}

test('practice mode changes reject old candidates and clear ready IDs immediately', async t => {
  const f = fixture(t, 'components/TargetedPracticePicker.vue')
  const first = f.page.refresh()
  f.page.changeMode('low_score')
  assert.deepEqual(f.events.filter(e=>e.name==='selected').map(e=>e.value.questionIds.length), [0, 0])
  f.pending[1].resolve({questionIds:['low'],actualCount:1,targetedContext:{...practice,mode:'low_score'}})
  await Vue.nextTick()
  f.pending[0].resolve({questionIds:['old-new'],actualCount:1,targetedContext:practice}); await first
  assert.equal(f.page.selection.value.questionIds[0], 'low')
})

test('account switch removes selected questions and cannot accept an old response', async t => {
  const f = fixture(t, 'components/TargetedPracticePicker.vue')
  const first = f.page.refresh()
  f.user.token = 'bob'
  f.pending[0].resolve({questionIds:['private'],actualCount:1,targetedContext:practice}); await first
  assert.equal(f.page.selection.value, null)
  assert.equal(f.events.filter(e=>e.name==='selected').at(-1).value.questionIds.length, 0)
})

test('detail account switch clears existing scores as well as late requests', async t => {
  const f = fixture(t, 'pages/targeted/performance.vue')
  let operation = f.page.load()
  f.pending[0].resolve({report:{analysisRevision:'r'},list:[{questionId:'private'}],total:1,current:1}); await operation
  operation = f.page.load()
  f.user.token = 'bob'
  assert.equal(f.page.records.value.length, 0)
  assert.equal(f.page.report.value, null)
  f.pending[1].resolve({report:{analysisRevision:'r'},list:[{questionId:'late-private'}],total:1,current:1}); await operation
  assert.equal(f.page.records.value.length, 0)
})

test('changed pagination revision reloads first page instead of mixing score snapshots', async t => {
  const f = fixture(t, 'pages/targeted/performance.vue')
  let operation = f.page.load()
  f.pending[0].resolve({report:{analysisRevision:'old'},list:[{questionId:'old'}],total:2,current:1}); await operation
  operation = f.page.load(true)
  f.pending[1].resolve({dataChanged:true,list:[{questionId:'new-page2'}]})
  await settle()
  assert.equal(f.pending[2].body.current, 1)
  f.pending[2].resolve({report:{analysisRevision:'new'},list:[{questionId:'new-page1'}],total:2,current:1}); await operation
  assert.equal(f.page.records.value.length, 1)
  assert.equal(f.page.records.value[0].questionId, 'new-page1')
})
