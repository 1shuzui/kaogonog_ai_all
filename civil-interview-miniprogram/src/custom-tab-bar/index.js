const { createNavigator } = require('./navigation.js')
const tokens = require('./tokens.js')
const tabs = require('./tabs.js')

function currentPage() {
  const pages = getCurrentPages()
  return pages[pages.length - 1]
}
function actualRoute() { return currentPage()?.route || '' }
const tabNavigator = createNavigator({
  readRoute: actualRoute,
  navigate(route, done) {
    wx.switchTab({
      url: '/' + route,
      success: () => done(true),
      fail: () => {
        done(false)
        wx.showToast({ title: '页面未切换，请重试', icon: 'none' })
      },
      complete: result => done(result?.errMsg === 'switchTab:ok')
    })
  },
  notify(state) { currentPage()?.getTabBar?.()?.renderState?.(state) }
})

Component({
  data: { tabs, ready: false, sheetOpen: false, selected: -1, visual: -1, moving: false, motion: 'full', layout: '' },
  lifetimes: {
    attached() { this.visible = false },
    ready() { this.visible = true; this.syncRoute() },
    detached() { this.visible = false; this.cancelMotion() }
  },
  pageLifetimes: {
    show() { this.visible = true; this.syncRoute() },
    hide() { this.visible = false; this.cancelMotion(); this.setData({ moving: false, ready: false }) },
    resize() { this.syncRoute() }
  },
  methods: {
    cancelMotion() {
      clearTimeout(this.motionTimer)
      this.motionVersion = (this.motionVersion || 0) + 1
      this.handoff = null
    },
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
      this.renderState(tabNavigator.sync(), true)
    },
    renderState(state, immediate = false) {
      if (!this.visible) return
      const selected = tabs.findIndex(tab => tab.pagePath === state.confirmed)
      if (selected < 0) return
      // Keep the old page selected until navigation arrives; the destination
      // owns the slide, so replacing the page cannot restart a half-played one.
      const visual = selected
      const transition = state.transition
      if (this.handoff && this.handoff.id === transition?.id && this.data.motion === 'full') {
        this.handoff.visual = visual
        return
      }
      if (immediate && transition?.id === this.transitionId && this.data.motion === 'full' &&
          this.data.ready && this.data.moving && this.data.selected === selected && this.data.visual === visual) return
      const from = tabs.findIndex(tab => tab.pagePath === transition?.from)
      if (immediate && this.data.motion === 'full' && transition?.to === state.confirmed &&
          transition.id !== this.transitionId && from >= 0 && from !== selected && Date.now() - transition.startedAt < 3000) {
        this.cancelMotion()
        this.transitionId = transition.id
        const version = this.motionVersion
        this.handoff = { id: transition.id, visual }
        // WeChat creates a separate tabBar for each page. Paint the prior tab
        // first, then move on the next frame; ready/show must not cancel it.
        this.setData({ selected, visual: from, ready: true, moving: false }, () => {
          if (!this.visible || version !== this.motionVersion) return
          this.motionTimer = setTimeout(() => {
            if (!this.visible || version !== this.motionVersion || !this.handoff) return
            const target = this.handoff.visual
            this.handoff = null
            this.setData({ visual: target, moving: true })
          }, 32)
        })
        return
      }
      this.cancelMotion()
      const moving = !immediate && this.data.ready && this.data.motion === 'full'
      if (this.data.selected === selected && this.data.visual === visual && this.data.ready && this.data.moving === moving) return
      this.setData({ selected, visual, ready: true, moving })
    },
    select(event) {
      if (this.data.sheetOpen) return
      const tab = tabs[Number(event.currentTarget.dataset.index)]
      if (tab) tabNavigator.request(tab.pagePath)
    }
  }
})
