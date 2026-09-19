import test from 'node:test'
import assert from 'node:assert/strict'
import { readFile } from 'node:fs/promises'

test('mini login keeps agreement and privacy callbacks after splitting password reset', async () => {
  const source = await readFile(new URL('../src/pages/login/index.vue', import.meta.url), 'utf8')
  for (const handler of ['toggleAgreement', 'onAgreePrivacyAuthorization', 'goLegalDocuments']) {
    assert.match(source, new RegExp(`function ${handler}\\(`))
  }
  const pages = JSON.parse(await readFile(new URL('../src/pages.json', import.meta.url), 'utf8'))
  assert.equal(pages.pages[0].path, 'pages/home/index')
  assert.ok(pages.pages.some(page => page.path === 'pages/login/reset'))
})
