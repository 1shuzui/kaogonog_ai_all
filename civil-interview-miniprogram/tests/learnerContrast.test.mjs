import test from 'node:test'
import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'

function contrast(a, b) {
  const light = hex => hex.match(/[a-f0-9]{2}/gi).map(x => parseInt(x, 16) / 255)
    .map(x => x <= .04045 ? x / 12.92 : ((x + .055) / 1.055) ** 2.4)
    .reduce((sum, x, i) => sum + x * [.2126, .7152, .0722][i], 0)
  const [x, y] = [light(a), light(b)].sort((a, b) => b - a)
  return (x + .05) / (y + .05)
}
test('learner semantic text colors meet 4.5:1 on their actual light surfaces', () => {
  const css = readFileSync(new URL('../src/styles/tokens.css', import.meta.url), 'utf8')
  const colors = Object.fromEntries([...css.matchAll(/--ui-([\w-]+):\s*(#[\da-f]{6})/gi)].map(([, key, value]) => [key, value]))
  for (const text of ['text', 'muted', 'link', 'error']) {
    for (const surface of ['bg', 'surface', 'soft']) {
      assert.ok(contrast(colors[text], colors[surface]) >= 4.5, `${text} on ${surface}`)
    }
  }
  assert.ok(contrast('#ffffff', colors.primary) >= 4.5, 'Primary button label')
})
