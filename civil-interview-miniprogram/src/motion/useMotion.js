import { computed, provide, inject, ref } from 'vue'
import { onHide, onReady, onResize, onShow, onUnload } from '@dcloudio/uni-app'
import tokens from './tokens.json'
import { bottomInset, motionStyle, normalizeMode } from './policy.mjs'

const motionKey = Symbol('learner-motion')
export const motionMode = ref(readMode())
function readMode() {
  try { return normalizeMode(uni.getStorageSync(tokens.storageKey)) } catch { return tokens.defaultMode }
}
export function setMotionMode(mode) {
  motionMode.value = normalizeMode(mode)
  try { uni.setStorageSync(tokens.storageKey, motionMode.value) } catch {}
  syncTabBar()
}
function syncTabBar() {
  // Resolve only the currently visible page instance, never cache getTabBar().
  const pages = typeof getCurrentPages === 'function' ? getCurrentPages() : []
  pages[pages.length - 1]?.getTabBar?.()?.syncRoute?.()
}
export function usePageMotion() {
  const visible = ref(false)
  const safeBottom = ref(0)
  function refresh() {
    motionMode.value = readMode()
    try { safeBottom.value = bottomInset(uni.getWindowInfo ? uni.getWindowInfo() : uni.getSystemInfoSync()) } catch {}
    syncTabBar()
  }
  onShow(() => { visible.value = true; refresh() })
  onReady(refresh) // native component ready also syncs itself if unavailable here
  onResize(refresh)
  onHide(() => { visible.value = false })
  onUnload(() => { visible.value = false })
  const motion = { mode: motionMode, visible }
  provide(motionKey, motion)
  return {
    ...motion,
    motionStyle: computed(() => motionStyle(motionMode.value, safeBottom.value)),
    motionClass: computed(() => [`motion-page--${motionMode.value}`, visible.value ? 'motion-page--visible' : 'motion-page--hidden'])
  }
}
export function useMotion() {
  return inject(motionKey, { mode: motionMode, visible: ref(true) })
}
