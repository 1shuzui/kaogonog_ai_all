import test from 'node:test'
import assert from 'node:assert/strict'
import {readFile} from 'node:fs/promises'
import vm from 'node:vm'
import * as billingUtils from '../src/utils/billing.js'
import * as constants from '../../civil-interview-miniprogram/src/utils/constants.js'

async function fixture(platform='frontend', stored) {
  const storage = stored || new Map([['username','acceptance-user']])
  const localStorage = {getItem:key=>storage.get(key)||null,setItem:(key,value)=>storage.set(key,value)}
  const uni = {getStorageSync:localStorage.getItem,setStorageSync:localStorage.setItem}
  const context = vm.createContext({localStorage,uni,Date})
  const module = new vm.SourceTextModule(await readFile(new URL(`../../civil-interview-${platform}/src/stores/billing.js`,import.meta.url),'utf8'),{context})
  await module.link(name=>{
    const values = name==='pinia' ? {defineStore:(_name,options)=>()=>{
      const state=options.state(), store={...state}
      Object.defineProperty(store,'$state',{get:()=>Object.fromEntries(Object.keys(state).map(key=>[key,store[key]]))})
      store.$patch=patch=>Object.assign(store,patch)
      Object.assign(store,options.actions)
      for(const [name,getter] of Object.entries(options.getters||{})) Object.defineProperty(store,name,{get:()=>getter.call(store,store)})
      return store
    }} : name.endsWith('/constants') ? constants : billingUtils
    return new vm.SyntheticModule(Object.keys(values),function(){for(const [key,value] of Object.entries(values)) this.setExport(key,value)},{context})
  })
  await module.evaluate()
  return {store:module.namespace.useBillingStore(),storage}
}

function manual() {
  return {planType:'manual',planName:'人工补发 30 分钟',isPaid:true,status:'active',remainingSeconds:1800,remainingMinutes:30,remainingDailyMinutes:30,dailyLimitMinutes:30,totalMinutes:30,monthlyExpireAt:Date.now()+86400000}
}

test('PC: a real manual-grant snapshot unlocks the requested practice route and survives reload',async()=>{
  const {store,storage}=await fixture()
  store.applyBackendState(manual())
  assert.equal(store.isPaid,true)
  assert.equal(store.canAccessRoute({name:'ExamPrepare',meta:{requiresPayment:true},query:{questionId:'real-question'}}),true)
  assert.equal(store.planLabel,'人工补发 30 分钟')
  assert.equal(store.isTrialOnly,false)
  const reloaded=(await fixture('frontend',storage)).store
  assert.equal(reloaded.isPaid,true)
  assert.equal(reloaded.planLabel,'人工补发 30 分钟')
  reloaded.resetToTrial()
  assert.equal(reloaded.isPaid,false)
})

test('PC: a server revocation wins over a paid package name and positive old balance',async()=>{
  const {store,storage}=await fixture()
  store.applyBackendState({...manual(),planType:'hourly',isPaid:false})
  assert.equal(store.isPaid,false)
  assert.equal(store.canAccessRoute({name:'Training',meta:{requiresPayment:true}}),false)
  assert.equal((await fixture('frontend',storage)).store.isPaid,false)
})

for(const [reason,patch] of [
  ['expired',{monthlyExpireAt:Date.now()-1000}],
  ['daily exhausted',{remainingDailyMinutes:0}],
  ['total exhausted',{remainingMinutes:0,remainingSeconds:0}],
]) test(`PC: cached server approval cannot override ${reason}`,async()=>{
  const {store}=await fixture()
  store.applyBackendState({...manual(),...patch})
  assert.equal(store.isPaid,false)
})

test('PC: legacy hourly/monthly snapshots remain compatible when the server flag is absent',async()=>{
  const {store}=await fixture()
  store.applyBackendState({planType:'hourly',remainingSeconds:600})
  assert.equal(store.isPaid,true)
  store.applyBackendState({planType:'monthly',monthlyExpireAt:Date.now()+10000})
  assert.equal(store.isPaid,true)
})

test('mini: manual access and its name come from the server snapshot',async()=>{
  const {store}=await fixture('miniprogram')
  store.applyBackendState(manual())
  assert.equal(store.isPaid,true)
  assert.equal(store.plan.title,'人工补发 30 分钟')
})

test('mini: a cached explicit revocation is not reversed by the hourly plan label',async()=>{
  const {store,storage}=await fixture('miniprogram')
  store.applyBackendState({...manual(),planType:'hourly',isPaid:false})
  assert.equal(store.isPaid,false)
  assert.equal((await fixture('miniprogram',storage)).store.isPaid,false)
})
