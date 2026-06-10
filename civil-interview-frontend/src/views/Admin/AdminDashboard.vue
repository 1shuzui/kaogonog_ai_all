<!--
PC 管理员工作台首页，把用户权益、调整流水、退款、定向入口、客服反馈和题库管理收束到一个后台入口。

这个页面只做导航和后台能力说明，不直接改数据；真正的补发、扣减、退款和题库编辑都进入各自页面后再触发。
这样管理员“我的”页不用散放多个入口，也方便后续把客服、财务、题库维护继续分区。

@param: 无；权限由路由守卫和后端管理员接口共同校验。
@return: 渲染管理员可进入的后台功能入口。
@raises: 不主动抛业务异常；非管理员访问由路由守卫拦截，接口错误由目标页面处理。
-->
<template>
  <div class="admin-dashboard page-container">
    <div class="admin-dashboard__header">
      <div>
        <span class="admin-dashboard__eyebrow">管理员工作台</span>
        <h2>后台管理</h2>
        <p>集中处理用户权益、售后退款、题库维护、定向入口和客服反馈。</p>
      </div>
      <a-button type="primary" @click="router.push('/admin/entitlements')">
        <UserOutlined /> 用户权益管理
      </a-button>
    </div>

    <div class="admin-dashboard__grid">
      <div
        v-for="item in adminCards"
        :key="item.path"
        class="card admin-card"
        @click="router.push(item.path)"
      >
        <component :is="item.icon" class="admin-card__icon" />
        <div class="admin-card__body">
          <h3>{{ item.title }}</h3>
          <p>{{ item.description }}</p>
        </div>
        <RightOutlined class="admin-card__arrow" />
      </div>
    </div>
  </div>
</template>

<script setup>
import { useRouter } from 'vue-router'
import {
  AimOutlined,
  CustomerServiceOutlined,
  DatabaseOutlined,
  FileSearchOutlined,
  HistoryOutlined,
  RightOutlined,
  UndoOutlined,
  UserOutlined
} from '@ant-design/icons-vue'

const router = useRouter()

const adminCards = [
  {
    title: '用户权益管理',
    description: '查询用户、补发人工权益、扣减指定权益剩余时长。',
    path: '/admin/entitlements',
    icon: UserOutlined
  },
  {
    title: '权益调整流水',
    description: '按用户、类型、操作者和时间核查人工调整记录。',
    path: '/admin/entitlement-adjustments',
    icon: HistoryOutlined
  },
  {
    title: '余额与退款',
    description: '核对订单剩余可退小时，并发起微信虚拟支付退款。',
    path: '/admin/refunds',
    icon: UndoOutlined
  },
  {
    title: '定向入口管理',
    description: '维护定向备面入口和重点分析发布内容。',
    path: '/admin/targeted',
    icon: AimOutlined
  },
  {
    title: '客服反馈',
    description: '处理题目报错、权益异常和体验反馈。',
    path: '/support',
    icon: CustomerServiceOutlined
  },
  {
    title: '题库管理',
    description: '检索、编辑、导入题库和真实题源元数据。',
    path: '/bank',
    icon: DatabaseOutlined
  },
  {
    title: '题库导入',
    description: '上传并导入标准模板题库文件。',
    path: '/bank/import',
    icon: FileSearchOutlined
  }
]
</script>

<style lang="less" scoped>
@import '@/styles/variables.less';

.admin-dashboard__header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
  margin-bottom: 18px;
}

.admin-dashboard__eyebrow {
  display: inline-flex;
  margin-bottom: 6px;
  color: @primary-color;
  font-size: @font-size-sm;
  font-weight: 600;
}

.admin-dashboard__header h2 {
  margin: 0;
  color: @text-primary;
  font-size: @font-size-xxl;
}

.admin-dashboard__header p {
  margin: 6px 0 0;
  color: @text-secondary;
}

.admin-dashboard__grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(260px, 1fr));
  gap: 14px;
}

.admin-card {
  display: grid;
  grid-template-columns: 42px minmax(0, 1fr) auto;
  gap: 12px;
  align-items: center;
  min-height: 118px;
  padding: 18px;
  cursor: pointer;
  transition: transform 0.2s, border-color 0.2s, box-shadow 0.2s;

  &:hover {
    transform: translateY(-2px);
    border-color: fade(@primary-color, 25%);
    box-shadow: @shadow-popup;
  }
}

.admin-card__icon {
  width: 42px;
  height: 42px;
  padding: 10px;
  border-radius: @border-radius;
  color: @primary-color;
  background: fade(@primary-color, 10%);
  font-size: 22px;
}

.admin-card__body h3 {
  margin: 0 0 6px;
  color: @text-primary;
  font-size: @font-size-lg;
}

.admin-card__body p {
  margin: 0;
  color: @text-secondary;
  line-height: 1.6;
}

.admin-card__arrow {
  color: @text-placeholder;
}
</style>
