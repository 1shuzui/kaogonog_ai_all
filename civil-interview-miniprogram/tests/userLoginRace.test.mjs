import test from 'node:test'
import assert from 'node:assert/strict'
import { readFile } from 'node:fs/promises'
import vm from 'node:vm'
import * as constants from '../src/utils/constants.js'

async function userFixture(platform, loadProfile = false) {
  const requests = [], profileRequests = [], writes = [], storage = new Map()
  const localStorage = {getItem:key=>storage.get(key)||null, setItem:(key,value)=>storage.set(key,value), removeItem:key=>storage.delete(key)}
  const uni = {getStorageSync:localStorage.getItem, setStorageSync:localStorage.setItem, removeStorageSync:localStorage.removeItem}
  const context = vm.createContext({localStorage,uni})
  const file = new URL(`../../civil-interview-${platform}/src/stores/user.js`, import.meta.url)
  const module = new vm.SourceTextModule(await readFile(file,'utf8'), {context})
  const request = () => new Promise((resolve,reject)=>requests.push({resolve,reject}))
  await module.link(name=> {
    let values
    if(name === 'pinia') values = {defineStore:(_name,options)=>()=>Object.assign(options.state(), options.actions)}
    else if(name.endsWith('/api/auth')) values = {login:request,loginWithWechat:request,register:request,bindWechatMiniProgram:request,bindWechatMiniProgramInvite:request,setupWechatMiniProgramAccount:request}
    else if(name.endsWith('/api/user')) values = {getUserInfo:()=>new Promise(resolve=>profileRequests.push(resolve)),getProvinces:async()=>[],updatePreferences:()=>new Promise(resolve=>writes.push(resolve)),updateUserProfile:()=>{ writes.push('profile') }}
    else if(name.endsWith('/utils/constants')) values = constants
    else if(name.endsWith('/utils/logger')) values = {logger:{warn(){},error(){}}}
    else {
      const id = name.split('/').at(-1)
      values = {[`use${id[0].toUpperCase()}${id.slice(1)}Store`]:()=>({$reset(){},reset(){},reloadForCurrentUser(){},resetToTrial(){}})}
    }
    return new vm.SyntheticModule(Object.keys(values),function(){ for(const [key,value] of Object.entries(values)) this.setExport(key,value) },{context})
  })
  await module.evaluate()
  const user = module.namespace.useUserStore()
  if (!loadProfile) user.loadUserInfo = async()=>{}
  return {user,requests,storage,profileRequests,writes}
}

for(const platform of ['frontend','miniprogram']) test(`${platform}: an old login cannot replace a newer account or restore a logged-out session`, async()=>{
  const {user,requests,storage} = await userFixture(platform)
  const first = user.login('alice','password')
  const obsolete = assert.rejects(first, error=>error.code==='STALE_SESSION')
  const second = platform==='miniprogram' ? user.loginWithWechat('wechat-code','terms') : user.login('bob','password')
  requests[1].resolve({access_token:'b-token',username:'bob',userId:'2'})
  await second
  requests[0].resolve({access_token:'a-token',username:'alice',userId:'1'})
  await obsolete
  assert.equal(user.username,'bob')
  assert.equal(storage.get('civil_user_id'),'2')
  const pending = user.login('alice','password')
  const cancelled = assert.rejects(pending,error=>error.code==='STALE_SESSION')
  user.logout()
  requests[2].resolve({access_token:'late-token',username:'alice',userId:'1'})
  await cancelled
  assert.equal(user.token,'')
  assert.equal(storage.has('civil_user_id'),false)
})

for (const platform of ['frontend', 'miniprogram']) test(`${platform}: late user info cannot change the new account's immutable ID or cached profile`, async()=>{
  const { user, storage, profileRequests } = await userFixture(platform, true)
  user.token = 'a-token'; user.userId = '1'; user.username = 'alice'
  const pending = user.loadUserInfo()
  const stale = assert.rejects(pending, error=>error.code==='STALE_SESSION')
  user.logout(); user.token='b-token'; user.userId='2'; user.username='bob'; storage.set('civil_user_id','2')
  profileRequests[0]({id:'alice',userId:'1',name:'Alice'})
  await stale
  assert.equal(user.userId,'2')
  assert.equal(user.username,'bob')
  assert.equal(storage.get('civil_user_id'),'2')
})

test('late WeChat account setup cannot replace a different signed-in account', async()=>{
  const { user, requests, storage } = await userFixture('miniprogram')
  user.token='a-token'; user.userId='1'; user.username='wxmp_a'
  const pending = user.setupWechatPcAccount({username:'alice',password:'password'})
  const stale = assert.rejects(pending, error=>error.code==='STALE_SESSION')
  user.logout(); user.token='b-token'; user.userId='2'; user.username='bob'; storage.set('civil_user_id','2')
  requests[0].resolve({access_token:'a-updated-token',username:'alice',userId:'1'})
  await stale
  assert.equal(user.token,'b-token')
  assert.equal(user.username,'bob')
  assert.equal(storage.get('civil_user_id'),'2')
})

for (const platform of ['frontend', 'miniprogram']) test(`${platform}: a late preferences response cannot send a second write using the next account`, async()=>{
  const { user, writes } = await userFixture(platform)
  user.token='a-token'; user.username='alice'
  const pending = user.savePreferences({province:'jiangsu'})
  const stale = assert.rejects(pending, error=>error.code==='STALE_SESSION')
  user.logout(); user.token='b-token'; user.username='bob'
  writes[0]()
  await stale
  assert.equal(writes.length,1)
})
