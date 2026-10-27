<!-- Compatibility route for saved focus links and post-login navigation. -->
<template>
  <view class="motion-page page" :class="motionClass" :style="motionStyle">
    <text class="page-title">方向弱点分析</text>
    <text class="page-desc">依据所选方向的已保存成绩，查看薄弱题型与擅长项，并开展针对练习。</text>
    <text v-if="checkingAccess" class="page-desc">正在确认账号权限，可随时返回。</text>
    <text v-if="accessError" class="ui-error">{{ accessError }}</text>
    <TargetedPerformancePanel />
    <button class="primary-button" :disabled="checkingAccess || store.status === 'loading'" @tap="loadFocus">刷新分析</button>
    <button class="ui-link" @tap="goBack">返回定向备面</button>
  </view>
</template>
<script setup>
import { nextTick, ref } from 'vue'
import { onLoad, onShow, onHide, onUnload, onPageScroll } from '@dcloudio/uni-app'
import TargetedPerformancePanel from '../../components/TargetedPerformancePanel.vue'
import { usePageMotion } from '../../motion/useMotion'
import { useTargetedPerformanceStore } from '../../stores/targetedPerformance'
import { useTargetedStore } from '../../stores/targeted'
import { useUserStore } from '../../stores/user'
import { useBillingStore } from '../../stores/billing'
import { useSubscriptionStore } from '../../stores/subscription'
import { decodeTargetRoute, buildTargetFocusUrl } from '../../utils/targetedOptions'
import { hasPremiumAccess } from '../../utils/access'
import { promptLoginForAction } from '../../utils/navigation'
const { motionClass, motionStyle } = usePageMotion()
const store = useTargetedPerformanceStore(), targetedStore = useTargetedStore(), userStore = useUserStore()
const billingStore = useBillingStore(), subscriptionStore = useSubscriptionStore()
const checkingAccess = ref(false), accessError = ref('')
let generation = 0, ready = false
function stopWaiting() { generation++; checkingAccess.value = false; store.cancel() }
onHide(stopWaiting); onUnload(stopWaiting)
onPageScroll(event => { store.scrollTop = event.scrollTop })
onLoad(options => {
  const restoredScrollTop = store.restorePosition ? store.scrollTop : null
  const payload = decodeTargetRoute(options || {})
  if (Object.keys(payload).length) targetedStore.setTarget(payload)
  store.setScope(Object.keys(payload).length ? payload : store.target || targetedStore.selectionPayload, options?.period === 'all' ? 'all' : store.period)
  if (restoredScrollTop !== null) store.scrollTop = restoredScrollTop
  ready = true
})
onShow(async () => {
  if (store.restorePosition) {
    store.restorePosition = false
    await nextTick()
    uni.pageScrollTo({ scrollTop: store.scrollTop, duration: 0 })
  }
  if (ready) loadFocus()
})
async function loadFocus() {
  if (!promptLoginForAction('分析方向弱点', buildTargetFocusUrl(store.target || {}) + '&period=' + store.period)) return
  const id = ++generation, token = userStore.token
  checkingAccess.value = true; accessError.value = ''
  await Promise.allSettled([userStore.loadUserInfo(), subscriptionStore.refresh({ skipErrorHandler: true })])
  if (id !== generation || token !== userStore.token) return
  checkingAccess.value = false
  if (!hasPremiumAccess(userStore, billingStore, subscriptionStore)) { accessError.value = '请先开通套餐后使用定向备面'; return }
  await store.fetch()
}
function goBack() { uni.navigateBack({ fail: () => uni.switchTab({ url: '/pages/targeted/index' }) }) }
</script>
