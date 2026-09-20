import test from 'node:test'
import assert from 'node:assert/strict'
import vm from 'node:vm'
import { readFile } from 'node:fs/promises'
async function api(response) {
  let options
  const context = vm.createContext({})
  const module = new vm.SourceTextModule(await readFile(new URL('../src/api/targeted.js', import.meta.url), 'utf8'), { context })
  await module.link(() => new vm.SyntheticModule(['request'], function () { this.setExport('request', async value => { options = value; return response }) }, { context }))
  await module.evaluate()
  return { ...module.namespace, options: () => options }
}
test('focus validates malformed JSON and structurally invalid successful responses', async () => {
  for (const response of ['<html>bad gateway</html>', {}, null, { questionCount: null }, { questionCount: 10, strategy: 'invalid' },
    { questionCount: 10, coreFocus: [null] }, { questionCount: 10, highFreqTypes: [null] },
    { questionCount: 10, focusAreas: [null] }, { questionCount: 10, strategy: [{}] }, { questionCount: 10, hotTopics: [null] }]) {
    const service = await api(response)
    await assert.rejects(service.getFocusAnalysis({ province: 'jiangsu' }), error => error.code === 'PARSE_ERROR')
  }
})
test('a business failure cannot be rendered as an empty or successful analysis', async () => {
  const service = await api({ success: false, message: '当前方向暂不可用' })
  await assert.rejects(service.getFocusAnalysis({}), error => error.code === 'BUSINESS_ERROR' && error.message === '当前方向暂不可用')
})
test('real empty analysis succeeds, forwards cancellation and keeps the existing 30s request contract', async () => {
  const response = { questionCount: 0, isFallback: true, coreFocus: [], strategy: [] }
  const service = await api(response), signal = {}
  assert.deepEqual(await service.getFocusAnalysis({}, { signal }), response)
  assert.equal(service.options().signal, signal)
  assert.equal(service.options().timeout, 30000)
  assert.equal(service.options().skipErrorHandler, true)
})
