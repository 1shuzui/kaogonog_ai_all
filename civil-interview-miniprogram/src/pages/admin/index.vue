<template>
  <view class="page">
    <text class="page-title">管理员中心</text>
    <text class="page-desc">管理退款和题库内容，权限以后端管理员校验为准。</text>

    <view v-if="userStore.isAdmin" class="menu-list">
      <view class="menu-item card" @tap="goRefunds">
        <view>
          <text class="menu-item__title">退款管理</text>
          <text class="menu-item__desc">查询可退额度并提交管理员退款</text>
        </view>
        <text class="menu-item__arrow">›</text>
      </view>
      <view class="menu-item card" @tap="goQuestions">
        <view>
          <text class="menu-item__title">题库管理</text>
          <text class="menu-item__desc">新增、编辑、删除手动题目</text>
        </view>
        <text class="menu-item__arrow">›</text>
      </view>
      <view class="menu-item card" @tap="goSupport">
        <view>
          <text class="menu-item__title">客服反馈后台</text>
          <text class="menu-item__desc">查看全站反馈并处理用户提交的问题</text>
        </view>
        <text class="menu-item__arrow">›</text>
      </view>
    </view>

    <view v-else class="card">
      <EmptyState title="无管理员权限" desc="请使用管理员账号登录后再访问。" />
    </view>
  </view>
</template>

<script setup>
import { onShow } from '@dcloudio/uni-app'
import EmptyState from '../../components/EmptyState.vue'
import { useUserStore } from '../../stores/user'
import { requireLogin } from '../../utils/navigation'

const userStore = useUserStore()

onShow(() => {
  if (!requireLogin()) return
  userStore.loadUserInfo().catch(() => null)
})

function goRefunds() {
  uni.navigateTo({ url: '/pages/admin/refunds' })
}

function goQuestions() {
  uni.navigateTo({ url: '/pages/admin/questions' })
}

function goSupport() {
  uni.navigateTo({ url: '/pages/support/index' })
}
</script>

<style scoped>
.menu-item {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 20rpx;
}

.menu-item__title,
.menu-item__desc {
  display: block;
}

.menu-item__title {
  color: #1a1a2e;
  font-size: 30rpx;
  font-weight: 800;
}

.menu-item__desc {
  margin-top: 8rpx;
  color: #6f7c8f;
  font-size: 24rpx;
}

.menu-item__arrow {
  color: #8c8c8c;
  font-size: 44rpx;
  line-height: 1;
}
</style>
