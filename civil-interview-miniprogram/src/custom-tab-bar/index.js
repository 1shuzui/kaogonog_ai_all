const { createNavigator } = require('./navigation.js')
const tokens = require('./tokens.js')
const tabs = require('./tabs.js')

function currentPage() {
  const pages = getCurrentPages()
  return pages[pages.length - 1]
}
function actualRoute() { return currentPage()?.route || '' }
const navigator = createNavigator({
  readRoute: actualRoute,
  navigate(route, done) {
    wx.switchTab({ url: '/' + route, success: () => done(true), fail: () => {
      done(false)
      wx.showToast({ title: '页面未切换，请重试', icon: 'none' })
    } })
  },
  notify(state) { currentPage()?.getTabBar?.()?.renderState(state) }
})

Component({
  data: { tabs, ready: false, sheetOpen: false, selected: -1, visual: -1, moving: false, motion: 'full', layout: '' },
  lifetimes: {
    attached() { this.visible = false },
    ready() { this.visible = true; this.syncRoute() },
    detached() { this.visible = false }
  },
  pageLifetimes: {
    show() { this.visible = true; this.syncRoute() },
    hide() { this.visible = false; this.setData({ moving: false, ready: false }) },
    resize() { this.syncRoute() }
  },
  methods: {
    setSheetOpen(open) {
      if (this.data.sheetOpen !== Boolean(open)) this.setData({ sheetOpen: Boolean(open) })
    },
    syncRoute() {
      this.setSheetOpen((currentPage()?.__learnerSheetCount || 0) > 0)
      let info = {}
      try { info = wx.getWindowInfo ? wx.getWindowInfo() : wx.getSystemInfoSync() } catch {}
      const inset = info.safeAreaInsets?.bottom ?? (info.safeArea ? info.screenHeight - info.safeArea.bottom : 0)
      const safe = Number.isFinite(inset) ? Math.max(0, inset) : 0
      let motion = tokens.defaultMode
      try { motion = wx.getStorageSync(tokens.storageKey) || motion } catch {}
      if (!['full', 'reduced', 'off'].includes(motion)) motion = tokens.defaultMode
      this.setData({ motion, layout: `bottom:${safe + tokens.navGapPx}px;height:${tokens.navHeightPx}px;--motion-press:${motion === 'off' ? 0 : tokens.press}ms;--motion-scale:${motion === 'full' ? tokens.pressScale : 1};--motion-segment:${motion === 'full' ? tokens.segment : 0}ms;--motion-ease:${tokens.easing};` })
      // A different page owns a different native tabBar: never replay index 0.
      this.renderState(navigator.sync(), true)
    },
    renderState(state, immediate = false) {
      if (!this.visible) return
      const selected = tabs.findIndex(tab => tab.pagePath === state.confirmed)
      if (selected < 0) return
      const pending = tabs.findIndex(tab => tab.pagePath === state.desired)
      const visual = state.pending && !immediate && pending >= 0 ? pending : selected
      const moving = !immediate && this.data.ready && this.data.motion === 'full'
      if (this.data.selected === selected && this.data.visual === visual && this.data.ready && this.data.moving === moving) return
      this.setData({ selected, visual, ready: true, moving })
    },
    select(event) {
      if (this.data.sheetOpen) return
      const tab = tabs[Number(event.currentTarget.dataset.index)]
      if (tab) navigator.request(tab.pagePath)
    }
  }
})
