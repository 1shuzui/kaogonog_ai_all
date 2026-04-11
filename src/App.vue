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
    <AppTabBar v-if="showTabBar" />
  </div>
</template>

<script setup>
import { computed, onMounted } from 'vue'
import { useRoute } from 'vue-router'
import { useUserStore } from '@/stores/user'
import http from '@/api/index'
import AppHeader from '@/components/layout/AppHeader.vue'
import AppTabBar from '@/components/layout/AppTabBar.vue'
import ErrorBoundary from '@/components/common/ErrorBoundary.vue'

const route = useRoute()
const userStore = useUserStore()

const layout = computed(() => route.meta.layout || 'default')
const layoutClass = computed(() => `layout-${layout.value}`)
const showHeader = computed(() => layout.value !== 'fullscreen' && layout.value !== 'blank')
const showTabBar = computed(() => layout.value === 'default')

// 启动时校验 token 有效性
onMounted(async () => {
  if (userStore.isAuthenticated) {
    try {
      await http.get('/user/me')
    } catch {
      // 401 会被 axios 拦截器自动处理（清除 token 并跳转登录页）
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

/* 页面过渡动画 */
.page-fade-enter-active,
.page-fade-leave-active {
  transition: opacity 0.25s ease;
}
.page-fade-enter-from,
.page-fade-leave-to {
  opacity: 0;
}
</style>
