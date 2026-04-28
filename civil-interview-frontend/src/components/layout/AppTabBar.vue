<template>
  <nav class="app-tabbar">
    <router-link
      v-for="tab in tabs"
      :key="tab.path"
      :to="tab.path"
      class="app-tabbar__item"
      :class="{ active: isActive(tab.path) }"
    >
      <component :is="tab.icon" class="app-tabbar__icon" />
      <span class="app-tabbar__label">{{ tab.label }}</span>
    </router-link>
  </nav>
</template>

<script setup>
import { useRoute } from 'vue-router'
import {
  HomeOutlined,
  AimOutlined,
  DatabaseOutlined,
  ThunderboltOutlined,
  UserOutlined
} from '@ant-design/icons-vue'

const route = useRoute()

const tabs = [
  { path: '/', label: '首页', icon: HomeOutlined },
  { path: '/targeted', label: '定向备面', icon: AimOutlined },
  { path: '/bank', label: '题库', icon: DatabaseOutlined },
  { path: '/training', label: '专项训练', icon: ThunderboltOutlined },
  { path: '/profile', label: '我的', icon: UserOutlined }
]

function isActive(path) {
  if (path === '/') return route.path === '/'
  return route.path.startsWith(path)
}
</script>

<style lang="less" scoped>
@import '@/styles/variables.less';

.app-tabbar {
  position: fixed;
  bottom: 0;
  left: 0;
  right: 0;
  z-index: 100;
  height: @tabbar-height;
  display: flex;
  align-items: center;
  justify-content: space-around;
  background: #fff;
  border-top: 1px solid @border-color;
  padding-bottom: env(safe-area-inset-bottom);
}

.app-tabbar__item {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  flex: 1;
  height: 100%;
  color: @text-secondary;
  text-decoration: none;
  transition: color 0.2s;

  &.active {
    color: @primary-color;
  }
}

.app-tabbar__icon {
  font-size: 20px;
  margin-bottom: 2px;
}

.app-tabbar__label {
  font-size: @font-size-xs;
}
</style>
