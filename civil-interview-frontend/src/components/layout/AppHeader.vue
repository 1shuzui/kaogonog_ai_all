<template>
  <header class="app-header">
    <div class="app-header__brand" @click="$router.push('/')">
      <SafetyCertificateOutlined class="app-header__icon" />
      <span class="app-header__title">公考面试AI测评</span>
    </div>
    <div class="app-header__actions">
      <a-button type="text" class="plan-trigger" @click="router.push('/pricing')">
        <WalletOutlined />
        <span class="hide-on-mobile">{{ planLabel }}</span>
      </a-button>
      <a-dropdown v-if="userStore.isAuthenticated && userStore.provinces.length">
        <a class="province-trigger" @click.prevent>
          <EnvironmentOutlined />
          <span class="hide-on-mobile">{{ userStore.provinceName }}</span>
        </a>
        <template #overlay>
          <a-menu @click="onProvinceChange">
            <a-menu-item v-for="p in userStore.provinces" :key="p.code">
              {{ p.name }}
            </a-menu-item>
          </a-menu>
        </template>
      </a-dropdown>
    </div>
  </header>
</template>

<script setup>
import { computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { SafetyCertificateOutlined, EnvironmentOutlined, WalletOutlined } from '@ant-design/icons-vue'
import { useUserStore } from '@/stores/user'
import { useBillingStore } from '@/stores/billing'

const router = useRouter()
const userStore = useUserStore()
const billingStore = useBillingStore()
const planLabel = computed(() => (userStore.isAdmin ? '管理员' : billingStore.planLabel))

onMounted(() => {
  if (userStore.isAuthenticated && !userStore.provinces.length) {
    userStore.loadProvinces().catch(() => {})
  }
})

async function onProvinceChange({ key }) {
  await userStore.persistProvince(key)
}
</script>

<style lang="less" scoped>
@import '@/styles/variables.less';

.app-header {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  z-index: 100;
  height: @header-height;
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0 16px;
  background: @primary-color;
  color: #fff;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.15);
}

.app-header__brand {
  display: flex;
  align-items: center;
  gap: 8px;
  cursor: pointer;
}

.app-header__icon {
  font-size: 22px;
}

.app-header__title {
  font-size: @font-size-lg;
  font-weight: 600;
  letter-spacing: 1px;
}

.app-header__actions {
  display: flex;
  align-items: center;
  gap: 8px;
}

.plan-trigger {
  color: rgba(255, 255, 255, 0.9);
  display: inline-flex;
  align-items: center;
  gap: 4px;
  height: 32px;
  border-radius: 16px;
  background: rgba(255, 255, 255, 0.15);

  &:hover {
    color: #fff;
    background: rgba(255, 255, 255, 0.25);
  }
}

.province-trigger {
  color: rgba(255, 255, 255, 0.9);
  display: flex;
  align-items: center;
  gap: 4px;
  font-size: @font-size-sm;
  padding: 4px 10px;
  border-radius: 16px;
  background: rgba(255, 255, 255, 0.15);
  transition: background 0.2s;

  &:hover {
    background: rgba(255, 255, 255, 0.25);
    color: #fff;
  }
}
</style>
