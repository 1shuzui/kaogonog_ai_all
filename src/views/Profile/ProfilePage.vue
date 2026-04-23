<template>
  <div class="profile-page page-container">
    <!-- 用户卡片 -->
    <div class="card profile-user">
      <div class="profile-user__avatar">
        {{ userInitial }}
      </div>
      <div class="profile-user__info">
        <h2>{{ userStore.userInfo?.name || userStore.username || '考生' }}</h2>
        <p v-if="userStore.email">{{ userStore.email }}</p>
      </div>
    </div>

    <!-- 数据概览 -->
    <div class="profile-stats" v-if="historyStore.stats">
      <div class="card profile-stat-item">
        <div class="profile-stat-item__value">{{ historyStore.stats.totalExams }}</div>
        <div class="profile-stat-item__label">练习次数</div>
      </div>
      <div class="card profile-stat-item">
        <div class="profile-stat-item__value">{{ historyStore.bestScore }}</div>
        <div class="profile-stat-item__label">最高分</div>
      </div>
      <div class="card profile-stat-item">
        <div class="profile-stat-item__value">{{ favoritesStore.items.length }}</div>
        <div class="profile-stat-item__label">收藏题目</div>
      </div>
    </div>

    <!-- 功能菜单 -->
    <div class="profile-menu">
      <div class="card menu-item" @click="$router.push('/profile/analysis')">
        <BarChartOutlined class="menu-item__icon" />
        <span class="menu-item__label">个人情况分析</span>
        <RightOutlined class="menu-item__arrow" />
      </div>
      <div class="card menu-item" @click="$router.push('/history')">
        <HistoryOutlined class="menu-item__icon" />
        <span class="menu-item__label">历史记录</span>
        <RightOutlined class="menu-item__arrow" />
      </div>
      <div class="card menu-item" @click="$router.push('/favorites')">
        <StarOutlined class="menu-item__icon" />
        <span class="menu-item__label">错题本 / 收藏夹</span>
        <RightOutlined class="menu-item__arrow" />
      </div>
      <div class="card menu-item" @click="$router.push('/profile/account')">
        <SettingOutlined class="menu-item__icon" />
        <span class="menu-item__label">账号管理</span>
        <RightOutlined class="menu-item__arrow" />
      </div>
    </div>

    <!-- 练习偏好 -->
    <div class="card profile-section">
      <h3>练习偏好</h3>
      <a-form layout="vertical">
        <a-form-item label="默认省份">
          <a-select v-model:value="userStore.selectedProvince" @change="onProvinceChange">
            <a-select-option v-for="p in userStore.provinces" :key="p.code" :value="p.code">
              {{ p.name }}
            </a-select-option>
          </a-select>
        </a-form-item>
        <a-form-item label="默认准备时间(秒)">
          <a-slider v-model:value="preferences.defaultPrepTime" :min="30" :max="300" :step="10" />
          <span class="pref-value">{{ preferences.defaultPrepTime }}s</span>
        </a-form-item>
        <a-form-item label="默认作答时间(秒)">
          <a-slider v-model:value="preferences.defaultAnswerTime" :min="60" :max="600" :step="10" />
          <span class="pref-value">{{ preferences.defaultAnswerTime }}s</span>
        </a-form-item>
      </a-form>
      <a-button type="primary" @click="savePreferences">保存设置</a-button>
    </div>

    <!-- 关于 -->
    <div class="card profile-section">
      <h3>关于</h3>
      <p style="color: #8C8C8C">公考面试AI智能测评系统 v1.0.0</p>
      <p style="color: #8C8C8C; font-size: 12px">基于结构化题库模板的AI精准评分系统</p>
    </div>

    <!-- 退出登录 -->
    <a-button danger block @click="handleLogout" style="margin-top: 12px">退出登录</a-button>
  </div>
</template>

<script setup>
import { reactive, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { BarChartOutlined, HistoryOutlined, StarOutlined, SettingOutlined, RightOutlined } from '@ant-design/icons-vue'
import { useUserStore } from '@/stores/user'
import { useHistoryStore } from '@/stores/history'
import { useFavoritesStore } from '@/stores/favorites'
import { message } from 'ant-design-vue'

const router = useRouter()
const userStore = useUserStore()
const historyStore = useHistoryStore()
const favoritesStore = useFavoritesStore()

const preferences = reactive({
  defaultPrepTime: 90,
  defaultAnswerTime: 180,
  enableVideo: true
})

const userInitial = computed(() => {
  const name = userStore.userInfo?.name || userStore.username || '考'
  return name.charAt(0).toUpperCase()
})

onMounted(async () => {
  try {
    await userStore.loadProvinces()
  } catch {}
  try {
    await userStore.loadUserInfo()
  } catch (e) {
    if (e?.response?.status === 401) {
      router.push('/login')
      return
    }
  }
  try {
    await historyStore.fetchStats()
  } catch {}
  Object.assign(preferences, userStore.preferences)
})

function onProvinceChange(code) {
  userStore.setProvince(code)
}

async function savePreferences() {
  await userStore.savePreferences({ ...preferences })
  message.success('设置已保存')
}

function handleLogout() {
  userStore.logout()
  router.push('/login')
}
</script>

<style lang="less" scoped>
@import '@/styles/variables.less';

.profile-user {
  display: flex;
  align-items: center;
  padding: 20px 16px;
  margin-bottom: 12px;
}

.profile-user__avatar {
  width: 56px;
  height: 56px;
  border-radius: 50%;
  background: linear-gradient(135deg, @primary-color 0%, @secondary-blue 100%);
  color: #fff;
  font-size: 24px;
  font-weight: 600;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
  margin-right: 16px;
}

.profile-user__info {
  h2 {
    font-size: @font-size-xl;
    color: @text-primary;
    margin-bottom: 2px;
  }
  p {
    font-size: @font-size-sm;
    color: @text-secondary;
    margin: 0;
  }
}

.profile-stats {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 10px;
  margin-bottom: 12px;
}

.profile-stat-item {
  text-align: center;
  padding: 12px 8px;
}

.profile-stat-item__value {
  font-size: @font-size-xl;
  font-weight: 700;
  color: @primary-color;
}

.profile-stat-item__label {
  font-size: @font-size-xs;
  color: @text-secondary;
  margin-top: 2px;
}

.profile-menu {
  display: flex;
  flex-direction: column;
  gap: 8px;
  margin-bottom: 16px;
}

.menu-item {
  display: flex;
  align-items: center;
  padding: 14px 16px;
  cursor: pointer;
  transition: box-shadow 0.2s;

  &:hover {
    box-shadow: @shadow-popup;
  }
}

.menu-item__icon {
  font-size: 20px;
  color: @primary-color;
  margin-right: 12px;
}

.menu-item__label {
  flex: 1;
  font-size: @font-size-base;
  color: @text-regular;
}

.menu-item__arrow {
  color: @text-secondary;
}

.profile-section {
  padding: 16px;
  margin-bottom: 12px;

  h3 {
    font-size: @font-size-lg;
    color: @text-primary;
    margin-bottom: 12px;
  }
}

.pref-value {
  display: inline-block;
  margin-left: 12px;
  font-size: @font-size-sm;
  color: @primary-color;
  font-weight: 600;
}
</style>
