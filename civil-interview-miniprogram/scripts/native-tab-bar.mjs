import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'

// uni-app's H5 custom-tab-bar is NOT the native WeChat custom tabBar.
// Emit only native WXML/WXSS/JS/JSON, for both watch builds and production.
export function nativeTabBar() {
  return {
    name: 'kaogong-native-tab-bar',
    apply: 'build',
    generateBundle() {
      if (process.env.UNI_PLATFORM !== 'mp-weixin') return
      const root = resolve('src')
      const emit = (fileName, path) => {
        this.addWatchFile(resolve(root, path))
        this.emitFile({ type: 'asset', fileName, source: readFileSync(resolve(root, path), 'utf8') })
      }
      for (const ext of ['js', 'json', 'wxml', 'wxss']) emit(`custom-tab-bar/index.${ext}`, `custom-tab-bar/index.${ext}`)
      emit('custom-tab-bar/navigation.js', 'custom-tab-bar/navigation.cjs')
      this.addWatchFile(resolve(root, 'motion/tokens.json'))
      this.emitFile({ type: 'asset', fileName: 'custom-tab-bar/tokens.js', source: `module.exports = ${readFileSync(resolve(root, 'motion/tokens.json'), 'utf8')}` })
      this.addWatchFile(resolve(root, 'pages.json'))
      const pages = JSON.parse(readFileSync(resolve(root, 'pages.json'), 'utf8'))
      const iconNames = ['home', 'environment', 'read', 'aim', 'solution']
      const tabs = pages.tabBar.list.map((tab, index) => ({ ...tab, learnerIcon: `static/learner-icons/${iconNames[index]}.svg` }))
      this.emitFile({ type: 'asset', fileName: 'custom-tab-bar/tabs.js', source: `module.exports = ${JSON.stringify(tabs)}` })
    }
  }
}
