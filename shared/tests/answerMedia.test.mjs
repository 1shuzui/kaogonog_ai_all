import test from 'node:test'
import assert from 'node:assert/strict'
import {resolveMediaUrl, resolveAnswerMedia} from '../answerMedia.mjs'

test('media paths respect the configured API gateway on both clients', () => {
  assert.equal(resolveMediaUrl('/uploads/clip.mp4','https://example.invalid/api'), 'https://example.invalid/api/uploads/clip.mp4')
  assert.equal(resolveMediaUrl('/uploads/clip.mp4','/api'), '/api/uploads/clip.mp4')
  assert.equal(resolveMediaUrl('/api/uploads/clip.mp4','https://example.invalid/api'), 'https://example.invalid/api/uploads/clip.mp4')
  assert.equal(resolveMediaUrl('wxfile://tmp/clip.mp4','/api'), 'wxfile://tmp/clip.mp4')
})
test('fresh uploaded media wins over older scoring metadata; historical and local video resolve', () => {
  assert.equal(resolveAnswerMedia({mediaUrl:'/uploads/new.mp4'}, {mediaRecord:{fileUrl:'/uploads/old.mp4',mediaType:'video/mp4'}}).url, '/api/uploads/new.mp4')
  assert.equal(resolveAnswerMedia({mediaUrl:'/uploads/history.mp4',mediaType:'video/mp4'}).kind,'video')
  assert.deepEqual(resolveAnswerMedia({filePath:'wxfile://tmp/a',mediaType:'video'}), {url:'wxfile://tmp/a',kind:'video',persisted:false})
})
