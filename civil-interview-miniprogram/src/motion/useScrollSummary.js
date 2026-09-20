import { getCurrentInstance, nextTick, ref, watch } from 'vue'
import { onReady, onResize, onShow, onHide, onUnload } from '@dcloudio/uni-app'
import { summaryState } from './policy.mjs'
import tokens from './tokens.json'

// For whole-page scrolling only. Exam room owns a scroll-view and does not use this.
export function useScrollSummary(selector, revision) {
  const { proxy } = getCurrentInstance()
  const compact = ref(false)
  let scrollTop = 0
  let threshold = Infinity
  let visible = false
  let measureId = 0
  let scrollVersion = 0
  function update() {
    const next = summaryState(compact.value, scrollTop, threshold)
    if (next !== compact.value) compact.value = next
  }
  async function calibrate() {
    const id = ++measureId
    await nextTick()
    if (!visible || id !== measureId) return
    const measuredAtScroll = scrollVersion
    uni.createSelectorQuery().in(proxy).select(selector).boundingClientRect().selectViewport().scrollOffset().exec(result => {
      if (!visible || id !== measureId) return
      const [rect, offset] = result || []
      if (!rect) { threshold = Infinity; update(); return }
      const measuredScrollTop = Number(offset?.scrollTop || 0)
      if (scrollVersion === measuredAtScroll) scrollTop = measuredScrollTop
      threshold = Math.max(tokens.summaryHysteresisPx, rect.bottom + measuredScrollTop - tokens.summaryHeightPx)
      update()
    })
  }
  // This uni-app compiler discovers onPageScroll only in the actual page SFC.
  function onSummaryScroll(event) { scrollVersion += 1; scrollTop = event.scrollTop; if (visible) update() }
  onShow(() => { visible = true; calibrate() })
  onReady(calibrate)
  onResize(calibrate)
  const stop = () => { visible = false; measureId += 1 }
  onHide(stop); onUnload(stop)
  if (revision) watch(revision, calibrate, { flush: 'post' })
  return { compact, calibrate, onSummaryScroll }
}
