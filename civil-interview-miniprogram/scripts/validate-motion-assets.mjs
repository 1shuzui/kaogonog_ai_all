import { existsSync, readFileSync } from 'node:fs'
import { join } from 'node:path'

export function validateMotionAssets(root) {
  const failures = []
  const read = name => existsSync(join(root, name)) ? readFileSync(join(root, name), 'utf8') : ''
  for (const file of ['index.js', 'index.json', 'index.wxml', 'index.wxss', 'navigation.js', 'tokens.js', 'tabs.js']) {
    if (!read(`custom-tab-bar/${file}`).trim()) failures.push(`missing native tabBar asset: ${file}`)
  }
  try {
    const app = JSON.parse(read('app.json'))
    if (app.tabBar?.custom !== true) failures.push('WeChat native custom tabBar must be enabled')
    for (const page of app.pages || []) {
      if (page.startsWith('pages/admin/')) continue
      if (!read(`${page}.wxml`).includes('motion-page')) failures.push(`learner motion root missing: ${page}`)
      if (['pages/home/index', 'pages/result/index'].includes(page)) {
        const hooks = Number(read(`${page}.js`).match(/__runtimeHooks\s*[:=]\s*(\d+)/)?.[1] || 0)
        if (!(hooks & 1)) failures.push(`native onPageScroll was not registered: ${page}`)
      }
    }
    const tabs = JSON.parse(read('custom-tab-bar/tabs.js').replace(/^module\.exports\s*=\s*/, '').replace(/;\s*$/, ''))
    if (JSON.stringify(tabs.map(x => x.pagePath)) !== JSON.stringify(app.tabBar.list.map(x => x.pagePath))) failures.push('native tabBar route configuration drifted')
  } catch { failures.push('invalid native tabBar configuration') }
  if (/require\([^)]*\.json['"]\)/.test(read('custom-tab-bar/index.js'))) failures.push('native WeChat JS cannot require JSON as a module')
  if (!read('app.wxss').includes('.motion-page--off')) failures.push('motion configuration CSS is missing from app.wxss')
  return failures
}
