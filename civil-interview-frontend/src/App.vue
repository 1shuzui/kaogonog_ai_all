<template>
  <div class="app-wrapper" :class="layoutClass">
    <AppHeader v-if="showHeader" />
    <main class="app-main">
      <ErrorBoundary>
        <router-view v-slot="{ Component }">
          <transition name="page-fade" mode="out-in">
            <component :is="Component" />
          </transition>
        </router-view>
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
const showHeader = computed(() => layout.value !== 'fullscreen' && layout.value !== 'blank')
const showTabBar = computed(() => layout.value === 'default')
const showPaywall = computed(() => billingStore.paywallVisible && !userStore.isAdmin)
const showProvinceGate = computed(() => {
  if (layout.value === 'blank') return false
  if (route.name === 'NotFound') return false
  return !userStore.hasConfirmedProvinceSelection
})

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
</style>
