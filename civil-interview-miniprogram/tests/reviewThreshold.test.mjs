import test from 'node:test'
import assert from 'node:assert/strict'
import { readFile } from 'node:fs/promises'
import vm from 'node:vm'
import * as constants from '../src/utils/constants.js'

async function userFixture() {
  const writes = [], storage = new Map()
  const context = vm.createContext({uni:{getStorageSync:key=>storage.get(key)||'',setStorageSync:(key,value)=>storage.set(key,value)}})
  const source = await readFile(new URL('../src/stores/user.js', import.meta.url),'utf8')
  const module = new vm.SourceTextModule(source, {context})
  await module.link(name=> {
    let values
    if(name === 'pinia') values = {defineStore:(_name,options)=>()=>Object.assign(options.state(), options.actions)}
    else if(name.endsWith('/api/auth')) values = Object.fromEntries(['login','loginWithWechat','register','bindWechatMiniProgram','bindWechatMiniProgramInvite','setupWechatMiniProgramAccount'].map(key=>[key,async()=>{}]))
    else if(name.endsWith('/api/user')) values = {getUserInfo:async()=>({}),getProvinces:async()=>[],updatePreferences:body=>new Promise((resolve,reject)=>writes.push({body,resolve,reject})),updateUserProfile:async()=>{}}
    else if(name.endsWith('/utils/constants')) values = constants
    else if(name.endsWith('/utils/logger')) values = {logger:{warn(){},error(){}}}
    else { const id=name.split('/').at(-1); values = {[`use${id[0].toUpperCase()}${id.slice(1)}Store`]:()=>({})} }
    return new vm.SyntheticModule(Object.keys(values),function(){ for(const [key,value] of Object.entries(values)) this.setExport(key,value) },{context})
  })
  await module.evaluate()
  const user = module.namespace.useUserStore()
  user.token='a-token'; user.username='alice'; user.userId='1'
  return {user,writes,storage}
}

test('threshold saves only its own field and persists only after success', async()=>{
  const {user,writes,storage} = await userFixture()
  const pending=user.saveReviewWeakThreshold(70)
  assert.equal(JSON.stringify(writes[0].body),'{"reviewWeakThresholdPercent":70}')
  assert.equal(user.preferences.reviewWeakThresholdPercent,60)
  writes[0].resolve({success:true}); await pending
  assert.equal(user.preferences.reviewWeakThresholdPercent,70)
  assert.equal(JSON.parse(storage.get('civil_user_preferences:guest')).reviewWeakThresholdPercent,70)
  const failed=user.saveReviewWeakThreshold(80)
  const rejection=assert.rejects(failed,/offline/)
  writes[1].reject(new Error('offline')); await rejection
  assert.equal(user.preferences.reviewWeakThresholdPercent,70)
})

test('exam settings preserve the threshold locally and never submit a stale threshold', async()=>{
  const {user,writes}=await userFixture()
  user.preferences.reviewWeakThresholdPercent=70
  const pending=user.savePreferences({defaultPrepTime:150})
  assert.equal('reviewWeakThresholdPercent' in writes[0].body,false)
  writes[0].resolve({success:true}); await pending
  assert.equal(user.preferences.reviewWeakThresholdPercent,70)
})

test('late threshold writes cannot update a new account',async()=>{
  const {user,writes,storage}=await userFixture()
  const pending=user.saveReviewWeakThreshold(70)
  const rejected=assert.rejects(pending,error=>error.code==='STALE_SESSION')
  user.token='b-token';user.username='bob';user.userId='2'
  writes[0].resolve({success:true}); await rejected
  assert.equal(user.preferences.reviewWeakThresholdPercent,60)
  assert.equal(storage.size,0)
})

test('invalid and logged-out settings never send a write',async()=>{
  const {user,writes}=await userFixture()
  for(const value of [0,101,69.5,NaN,'70',true]) await assert.rejects(user.saveReviewWeakThreshold(value))
  user.token=''; await assert.rejects(user.saveReviewWeakThreshold(70),/登录/)
  assert.equal(writes.length,0)
})

async function pageFixture({saveFails=false,refreshFails=false}={}) {
  const saves=[],toasts=[]
  const user={token:'a',preferences:{reviewWeakThresholdPercent:70},saveReviewWeakThreshold:async value=>{saves.push(value);if(saveFails)throw new Error('网络失败');user.preferences.reviewWeakThresholdPercent=value},loadUserInfo:async()=>{}}
  const favorites={load:async()=>!refreshFails,error:''}
  const context=vm.createContext({})
  const file=await readFile(new URL('../src/pages/favorites/index.vue',import.meta.url),'utf8')
  const script=file.match(/<script setup>([\s\S]*?)<\/script>/)[1]
  const module=new vm.SourceTextModule(script+'\nexport {openThreshold,closeThreshold,resetThresholdDraft,saveThreshold,thresholdDraft,thresholdOpen,thresholdError};',{context})
  await module.link(name=>{
    let values
    if(name==='vue') values={ref:value=>({value}),computed:fn=>({get value(){return fn()}})}
    else if(name==='@dcloudio/uni-app')values={onShow:()=>{}}
    else if(name.endsWith('/stores/user'))values={useUserStore:()=>user}
    else if(name.endsWith('/stores/favorites'))values={useFavoritesStore:()=>favorites}
    else if(name.endsWith('/motion/useMotion'))values={usePageMotion:()=>({})}
    else if(name.endsWith('/utils/navigation'))values={promptLoginForAction:()=>true,toast:(...args)=>toasts.push(args)}
    else if(name.endsWith('/utils/format'))values={formatDate:()=>''}
    else values={default:{}}
    return new vm.SyntheticModule(Object.keys(values),function(){for(const [key,value] of Object.entries(values))this.setExport(key,value)},{context})
  })
  await module.evaluate()
  return {page:module.namespace,user,favorites,saves,toasts}
}

test('reset edits the draft only and invalid input stays in the settings sheet',async()=>{
  const {page,user,saves}=await pageFixture()
  page.openThreshold(); page.resetThresholdDraft()
  assert.equal(page.thresholdDraft.value,'60');assert.equal(user.preferences.reviewWeakThresholdPercent,70)
  page.thresholdDraft.value='69.5';await page.saveThreshold()
  assert.match(page.thresholdError.value,/整数/);assert.equal(saves.length,0);assert.equal(page.thresholdOpen.value,true)
})

test('failed saves keep the sheet and prior setting, with an explicit failure',async()=>{
  const {page,user}=await pageFixture({saveFails:true})
  page.openThreshold();page.thresholdDraft.value='60';await page.saveThreshold()
  assert.equal(page.thresholdOpen.value,true);assert.equal(user.preferences.reviewWeakThresholdPercent,70)
  assert.match(page.thresholdError.value,/未保存.*网络失败/)
})

test('saved settings with failed refresh clearly report both outcomes',async()=>{
  const {page,user,favorites}=await pageFixture({refreshFails:true})
  page.openThreshold();page.thresholdDraft.value='60';await page.saveThreshold()
  assert.equal(user.preferences.reviewWeakThresholdPercent,60);assert.equal(page.thresholdOpen.value,false)
  assert.match(favorites.error,/已保存.*刷新失败/)
})
