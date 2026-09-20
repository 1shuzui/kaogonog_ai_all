import test from 'node:test'
import assert from 'node:assert/strict'
import * as options from '../src/utils/targetedOptions.js'

test('focus deep links retain city filters, multi-year selection, zero prep time and timing fields', () => {
  const target = options.findTargetByCode(options.DEFAULT_TARGETED_POSITION_TREE, 'sd_sydw_jinan')
  const payload = options.normalizeTargetPayload({ ...target, year: ['2025', '2026'], prepTime: 0 })
  const url = options.buildTargetFocusUrl(payload)
  const raw = Object.fromEntries(url.split('?')[1].split('&').map(part => part.split('=')))
  const decoded = options.decodeTargetRoute(raw)
  assert.deepEqual(options.normalizeTargetPayload(decoded), payload)
  assert.equal(decoded.subcategory, '济南')
  assert.equal(decoded.prepTime, '0')
  assert.equal(decoded.answerTime, '420')
  assert.equal(options.decodeTargetRoute({ unrelated: 'ignored', province: 'jiangsu' }).unrelated, undefined)
})
