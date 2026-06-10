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
import { computed, onMounted } from 'vue'
import { useRoute } from 'vue-router'
import { useUserStore } from '@/stores/user'
import { useBillingStore } from '@/stores/billing'
import AppHeader from '@/components/layout/AppHeader.vue'
import AppTabBar from '@/components/layout/AppTabBar.vue'
import ErrorBoundary from '@/components/common/ErrorBoundary.vue'
import BillingPaywallModal from '@/components/billing/BillingPaywallModal.vue'
import ProvinceGateModal from '@/components/common/ProvinceGateModal.vue'

const route = useRoute()
const userStore = useUserStore()
const billingStore = useBillingStore()

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
