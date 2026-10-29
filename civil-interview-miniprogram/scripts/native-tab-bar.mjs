import { readFileSync, writeFileSync } from 'node:fs'
import { resolve } from 'node:path'
import { transformWithEsbuild } from 'vite'

// uni-app's H5 custom-tab-bar is NOT the native WeChat custom tabBar.
// Emit only native WXML/WXSS/JS/JSON, for both watch builds and production.
export function nativeTabBar() {
  return {
    name: 'kaogong-native-tab-bar',
    apply: 'build',
    async generateBundle() {
      if (process.env.UNI_PLATFORM !== 'mp-weixin') return
      const root = resolve('src')
      const emit = async (fileName, path) => {
        this.addWatchFile(resolve(root, path))
        const source = readFileSync(resolve(root, path), 'utf8')
        const output = fileName.endsWith('.js')
          ? (await transformWithEsbuild(source, fileName, { target: 'es2018', sourcemap: false })).code
          : source
        this.emitFile({ type: 'asset', fileName, source: output })
      }
      for (const ext of ['js', 'json', 'wxml', 'wxss']) await emit(`custom-tab-bar/index.${ext}`, `custom-tab-bar/index.${ext}`)
      await emit('custom-tab-bar/navigation.js', 'custom-tab-bar/navigation.cjs')
      this.addWatchFile(resolve(root, 'motion/tokens.json'))
      this.emitFile({ type: 'asset', fileName: 'custom-tab-bar/tokens.js', source: `module.exports = ${readFileSync(resolve(root, 'motion/tokens.json'), 'utf8')}` })
      this.addWatchFile(resolve(root, 'pages.json'))
      const pages = JSON.parse(readFileSync(resolve(root, 'pages.json'), 'utf8'))
      const iconNames = ['home', 'environment', 'read', 'aim', 'solution']
      const tabs = pages.tabBar.list.map((tab, index) => ({ ...tab, learnerIcon: `static/learner-icons/${iconNames[index]}.svg` }))
      this.emitFile({ type: 'asset', fileName: 'custom-tab-bar/tabs.js', source: `module.exports = ${JSON.stringify(tabs)}` })
    },
    writeBundle: {
      order: 'post',
      sequential: true,
      handler(options, bundle) {
        if (process.env.UNI_PLATFORM !== 'mp-weixin') return
        // uni-app copies custom-tab-bar during writeBundle, after asset emission.
        // Restore our compiled scripts after that copy has finished.
        for (const asset of Object.values(bundle)) {
          if (asset.type === 'asset' && asset.fileName.startsWith('custom-tab-bar/') && asset.fileName.endsWith('.js')) {
            writeFileSync(resolve(options.dir, asset.fileName), asset.source)
          }
        }
      }
    }
  }
}
