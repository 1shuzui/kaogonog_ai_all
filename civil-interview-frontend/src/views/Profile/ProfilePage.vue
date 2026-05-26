<template>
  <div class="profile-page page-container">
    <!-- 用户卡片 -->
    <div class="card profile-user">
      <div class="profile-user__avatar">
        {{ userInitial }}
      </div>
      <div class="profile-user__info">
        <div class="profile-user__name-row">
          <h2>{{ userStore.userInfo?.name || userStore.username || '考生' }}</h2>
          <a-tag v-if="userStore.isAdmin" color="gold">管理员</a-tag>
        </div>
        <p v-if="userStore.email">{{ userStore.email }}</p>
        <p v-if="userStore.isAdmin" class="profile-user__role-tip">已启用管理员权限与完整功能访问</p>
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

    <div class="card balance-card">
      <div class="balance-card__main">
        <span class="balance-card__label">当前权益余额</span>
        <strong>{{ balanceTitle }}</strong>
        <p>{{ balanceDescription }}</p>
      </div>
      <a-button type="primary" @click="$router.push('/pricing')">查看套餐</a-button>
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
      <div class="card menu-item" @click="$router.push('/support')">
        <CustomerServiceOutlined class="menu-item__icon" />
        <span class="menu-item__label">{{ userStore.isAdmin ? '客服反馈后台' : '客服反馈中心' }}</span>
        <RightOutlined class="menu-item__arrow" />
      </div>
      <div class="card menu-item" @click="$router.push('/profile/orders')">
        <WalletOutlined class="menu-item__icon" />
        <span class="menu-item__label">订单记录</span>
        <RightOutlined class="menu-item__arrow" />
      </div>
      <div v-if="userStore.isAdmin" class="card menu-item" @click="$router.push('/admin/refunds')">
        <UndoOutlined class="menu-item__icon" />
        <span class="menu-item__label">余额与退款</span>
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
        <a-form-item label="注重题型">
          <a-select
            v-model:value="preferences.preferredQuestionDimensions"
            mode="multiple"
            placeholder="不选则随机"
            :max-tag-count="3"
          >
            <a-select-option v-for="item in questionTypeOptions" :key="item.key" :value="item.key">
              {{ item.name }}
            </a-select-option>
          </a-select>
        </a-form-item>
      </a-form>
      <a-button type="primary" @click="savePreferences">保存设置</a-button>
    </div>

    <div class="card profile-section">
      <h3>客服与反馈</h3>
      <SupportCenterPanel />
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
import {
  BarChartOutlined,
  CustomerServiceOutlined,
  HistoryOutlined,
  StarOutlined,
  SettingOutlined,
  UndoOutlined,
  WalletOutlined,
  RightOutlined
} from '@ant-design/icons-vue'
import { useUserStore } from '@/stores/user'
import { useHistoryStore } from '@/stores/history'
import { useFavoritesStore } from '@/stores/favorites'
import { useBillingStore } from '@/stores/billing'
import SupportCenterPanel from '@/components/common/SupportCenterPanel.vue'
import { message } from 'ant-design-vue'
import { QUESTION_CATEGORIES } from '@/utils/constants'

const router = useRouter()
const userStore = useUserStore()
const historyStore = useHistoryStore()
const favoritesStore = useFavoritesStore()
const billingStore = useBillingStore()

const preferences = reactive({
  defaultPrepTime: 90,
  defaultAnswerTime: 180,
  enableVideo: true,
  preferredQuestionDimensions: [],
  practicePreferenceConfirmed: false
})
const questionTypeOptions = QUESTION_CATEGORIES.filter((item) => item.key)

const userInitial = computed(() => {
  const name = userStore.userInfo?.name || userStore.username || '考'
  return name.charAt(0).toUpperCase()
})

const balanceTitle = computed(() => {
  if (userStore.isAdmin) return '管理员完整权限'
  return billingStore.planStatusText
})

const balanceDescription = computed(() => {
  if (userStore.isAdmin) return '管理员账号不扣减套餐余额，可访问全部训练与管理功能。'
  const billing = userStore.userInfo?.billing || {}
  const daily = Number(billing.remainingDailyMinutes || 0)
  const total = Number(billing.remainingMinutes || 0)
  if (daily > 0 || total > 0) {
    return `剩余总时长 ${total} 分钟，今日可用 ${daily || total} 分钟。`
  }
  return billingStore.activePlanDescription
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
  await userStore.savePreferences({
    ...preferences,
    practicePreferenceConfirmed: true
  })
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
  .profile-user__name-row {
    display: flex;
    align-items: center;
    gap: 8px;
    margin-bottom: 2px;
  }

  h2 {
    font-size: @font-size-xl;
    color: @text-primary;
    margin: 0;
  }
  p {
    font-size: @font-size-sm;
    color: @text-secondary;
    margin: 0;
  }
}

.profile-user__role-tip {
  margin-top: 4px !important;
  color: @primary-color !important;
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

.balance-card {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
  padding: 16px;
  margin-bottom: 12px;
}

.balance-card__main {
  min-width: 0;

  strong {
    display: block;
    margin-top: 4px;
    color: @text-primary;
    font-size: @font-size-lg;
  }

  p {
    margin: 4px 0 0;
    color: @text-secondary;
    font-size: @font-size-sm;
  }
}

.balance-card__label {
  color: @primary-color;
  font-size: @font-size-xs;
  font-weight: 700;
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
