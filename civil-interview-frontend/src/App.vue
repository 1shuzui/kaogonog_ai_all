<!--
PC 端应用外壳，负责统一页头、主体区域、错误边界、省份引导弹窗和权益拦截弹窗。

这里不要塞具体业务流程：考试、支付、题库、管理员工作台都应该留在各自页面和 store。
它只根据路由 meta 和全局状态决定是否显示通用框架，避免登录页、考场页和普通页面互相污染布局。

@param: 无；页面状态来自路由、Pinia 和全局弹窗 store。
@return: 渲染当前路由组件及必要的全局外壳组件。
@raises: 不主动抛业务异常；运行时异常由 ErrorBoundary 和请求层承接。
-->
<template>
  <div class="app-wrapper" :class="layoutClass">
    <AppHeader v-if="showHeader" />
    <main class="app-main">
      <ErrorBoundary>
        <router-view v-if="shouldRenderRouteContent" v-slot="{ Component }">
          <transition name="page-fade" mode="out-in">
            <component :is="Component" />
          </transition>
        </router-view>
        <div v-else class="province-gate-placeholder"></div>
      </ErrorBoundary>
    </main>
    <ProvinceGateModal :open="showProvinceGate" />
    <BillingPaywallModal v-if="showPaywall" />
    <AppTabBar v-if="showTabBar" />
  </div>
</template>

<script setup>
import { computed, onMounted, onUnmounted, watch } from 'vue'
import { useRoute } from 'vue-router'
import { useUserStore } from '@/stores/user'
import { useBillingStore } from '@/stores/billing'
import { reportDashboardHeartbeat } from '@/api/dashboard'
import AppHeader from '@/components/layout/AppHeader.vue'
import AppTabBar from '@/components/layout/AppTabBar.vue'
import ErrorBoundary from '@/components/common/ErrorBoundary.vue'
import BillingPaywallModal from '@/components/billing/BillingPaywallModal.vue'
import ProvinceGateModal from '@/components/common/ProvinceGateModal.vue'

const HEARTBEAT_INTERVAL_MS = 60 * 1000
const HEARTBEAT_SESSION_KEY = 'civil_dashboard_session_id'

const route = useRoute()
const userStore = useUserStore()
const billingStore = useBillingStore()
let heartbeatTimer = null
let heartbeatLastAt = Date.now()

function createHeartbeatId() {
  if (typeof crypto !== 'undefined' && typeof crypto.randomUUID === 'function') {
    return crypto.randomUUID()
  }
  return `${Date.now().toString(36)}-${Math.random().toString(36).slice(2, 10)}`
}

function getHeartbeatSessionId() {
  try {
    const existing = sessionStorage.getItem(HEARTBEAT_SESSION_KEY)
    if (existing) return existing
    const created = createHeartbeatId()
    sessionStorage.setItem(HEARTBEAT_SESSION_KEY, created)
    return created
  } catch {
    return createHeartbeatId()
  }
}

const layout = computed(() => route.meta.layout || 'default')
const layoutClass = computed(() => `layout-${layout.value}`)
const hasResolvedProvince = computed(() => {
  const province = String(userStore.selectedProvince || '').trim()
  if (!province || province === 'national') return false
  if (!userStore.provinces.length) return true
  return userStore.provinces.some((item) => item.code === province)
})
const showProvinceGate = computed(() => {
  if (!userStore.isAuthenticated) return false
  if (layout.value === 'blank') return false
  if (route.name === 'NotFound') return false
  return !userStore.hasConfirmedProvinceSelection
    || !hasResolvedProvince.value
    || userStore.preferences?.practicePreferenceConfirmed !== true
})
const isProvinceGateBlocking = computed(() => showProvinceGate.value && layout.value !== 'blank')
const shouldRenderRouteContent = computed(() => !isProvinceGateBlocking.value)
const showHeader = computed(() => (
  !isProvinceGateBlocking.value
  && layout.value !== 'fullscreen'
  && layout.value !== 'blank'
))
const showTabBar = computed(() => !isProvinceGateBlocking.value && layout.value === 'default')
const showPaywall = computed(() => billingStore.paywallVisible && !userStore.isAdmin)
const shouldTrackHeartbeat = computed(() => (
  userStore.isAuthenticated
  && typeof document !== 'undefined'
  && document.visibilityState === 'visible'
))

async function flushDashboardHeartbeat(forceSeconds = 0) {
  if (!userStore.isAuthenticated) {
    heartbeatLastAt = Date.now()
    return
  }
  const now = Date.now()
  const elapsedSeconds = forceSeconds || Math.round((now - heartbeatLastAt) / 1000)
  heartbeatLastAt = now
  if (elapsedSeconds <= 0) return

  try {
    await reportDashboardHeartbeat({
      sessionId: getHeartbeatSessionId(),
      eventId: createHeartbeatId(),
      clientType: 'pc',
      routePath: route.fullPath,
      durationSeconds: elapsedSeconds,
      activeAt: new Date(now).toISOString()
    })
  } catch {
    // heartbeat is best-effort and should never interrupt the current page
  }
}

function stopDashboardHeartbeat() {
  if (heartbeatTimer) {
    clearInterval(heartbeatTimer)
    heartbeatTimer = null
  }
}

function startDashboardHeartbeat() {
  if (!shouldTrackHeartbeat.value || heartbeatTimer) return
  heartbeatLastAt = Date.now()
  heartbeatTimer = window.setInterval(() => {
    if (!shouldTrackHeartbeat.value) return
    flushDashboardHeartbeat(60)
  }, HEARTBEAT_INTERVAL_MS)
}

function refreshDashboardHeartbeat() {
  stopDashboardHeartbeat()
  if (shouldTrackHeartbeat.value) {
    startDashboardHeartbeat()
  }
}

function handleVisibilityChange() {
  if (document.visibilityState === 'hidden') {
    flushDashboardHeartbeat()
    stopDashboardHeartbeat()
    return
  }
  refreshDashboardHeartbeat()
}

function handleBeforeUnload() {
  flushDashboardHeartbeat()
}

onMounted(async () => {
  try {
    if (!userStore.provinces.length) {
      await userStore.loadProvinces()
    }
  } catch {
    // ignore province loading failure here
  }

  if (userStore.isAuthenticated) {
    try {
      await userStore.loadUserInfo()
    } catch {
      // handled by the axios interceptor
    }
  }

  document.addEventListener('visibilitychange', handleVisibilityChange)
  window.addEventListener('beforeunload', handleBeforeUnload)
  refreshDashboardHeartbeat()
})

watch(
  () => [userStore.isAuthenticated, route.fullPath],
  () => {
    flushDashboardHeartbeat()
    refreshDashboardHeartbeat()
  }
)

onUnmounted(() => {
  flushDashboardHeartbeat()
  stopDashboardHeartbeat()
  document.removeEventListener('visibilitychange', handleVisibilityChange)
  window.removeEventListener('beforeunload', handleBeforeUnload)
})
</script>

<style lang="less">
.app-wrapper {
  min-height: 100vh;
  background: @page-bg;
  display: flex;
  flex-direction: column;
}

.app-main {
  flex: 1;
  padding-bottom: env(safe-area-inset-bottom);
}

.layout-default .app-main {
  padding-top: 56px;
  padding-bottom: 60px;
}

.layout-simple .app-main {
  padding-top: 56px;
}

.layout-fullscreen .app-main {
  padding: 0;
}

.layout-blank .app-main {
  padding: 0;
}

.page-fade-enter-active,
.page-fade-leave-active {
  transition: opacity 0.25s ease;
}

.page-fade-enter-from,
.page-fade-leave-to {
  opacity: 0;
}

.province-gate-placeholder {
  min-height: 100vh;
}
</style>
