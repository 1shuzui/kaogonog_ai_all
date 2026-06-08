<!--
这个底部导航服务移动宽度下的网页端入口切换，保持首页、练习、我的等入口位置稳定。

@param: 无；页面运行时从 props、路由参数、Pinia 状态和用户点击中拿数据。
@return: 渲染当前业务界面，并把按钮、表单或跳转事件交给既有流程处理。
@raises: 不主动抛业务异常；接口失败、未登录和权限不足由请求层或页面提示承接。
-->
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
