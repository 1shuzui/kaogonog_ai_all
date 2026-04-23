<template>
  <div class="billing-orders page-container">
    <div class="billing-orders__header">
      <a-button type="text" @click="$router.back()">
        <LeftOutlined /> 返回
      </a-button>
      <h2>订单记录</h2>
    </div>

    <div class="card billing-orders__summary">
      <span class="billing-orders__eyebrow">当前套餐</span>
      <h3>{{ billingStore.planLabel }}</h3>
      <p>{{ billingStore.planStatusText }}</p>
      <a-button type="primary" @click="$router.push('/pricing')">查看套餐</a-button>
    </div>

    <div v-if="billingStore.recentOrders.length" class="billing-orders__list">
      <div v-for="order in billingStore.recentOrders" :key="order.id" class="card billing-order-item">
        <div class="billing-order-item__main">
          <div class="billing-order-item__title-row">
            <h3>{{ order.title }}</h3>
            <a-tag color="green">已支付</a-tag>
          </div>
          <p>{{ order.summary }}</p>
          <div class="billing-order-item__meta">
            <span>订单号：{{ order.id }}</span>
            <span>金额：¥{{ order.amount }}</span>
            <span>时间：{{ formatOrderTime(order.createdAt) }}</span>
          </div>
        </div>
      </div>
    </div>

    <EmptyState v-else text="暂无本地订单记录，请先前往套餐页开通。">
      <template #action>
        <a-button type="primary" @click="$router.push('/pricing')">去开通</a-button>
      </template>
    </EmptyState>
  </div>
</template>

<script setup>
import { LeftOutlined } from '@ant-design/icons-vue'
import { useBillingStore } from '@/stores/billing'
import EmptyState from '@/components/common/EmptyState.vue'

const billingStore = useBillingStore()

function formatOrderTime(timestamp) {
  const date = new Date(Number(timestamp) || Date.now())
  const year = date.getFullYear()
  const month = String(date.getMonth() + 1).padStart(2, '0')
  const day = String(date.getDate()).padStart(2, '0')
  const hour = String(date.getHours()).padStart(2, '0')
  const minute = String(date.getMinutes()).padStart(2, '0')
  return `${year}-${month}-${day} ${hour}:${minute}`
}
</script>

<style lang="less" scoped>
@import '@/styles/variables.less';

.billing-orders__header {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 16px;
}

.billing-orders__header h2 {
  margin: 0;
  color: @text-primary;
  font-size: @font-size-xl;
}

.billing-orders__summary {
  padding: 18px 16px;
  margin-bottom: 14px;
  border: 1px solid rgba(27, 95, 170, 0.08);
  box-shadow: 0 18px 36px rgba(21, 66, 126, 0.08);
}

.billing-orders__summary h3 {
  margin: 8px 0 4px;
  color: @text-primary;
  font-size: @font-size-lg;
}

.billing-orders__summary p {
  color: @text-secondary;
  line-height: 1.8;
  margin-bottom: 12px;
}

.billing-orders__eyebrow {
  display: inline-flex;
  align-items: center;
  padding: 4px 10px;
  border-radius: 999px;
  background: rgba(27, 95, 170, 0.1);
  color: @primary-color;
  font-size: @font-size-xs;
  font-weight: 600;
}

.billing-orders__list {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.billing-order-item {
  padding: 16px;
  border: 1px solid rgba(27, 95, 170, 0.08);
  box-shadow: 0 16px 30px rgba(21, 66, 126, 0.08);
}

.billing-order-item__title-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 12px;
  margin-bottom: 6px;
}

.billing-order-item__title-row h3 {
  margin: 0;
  color: @text-primary;
  font-size: @font-size-lg;
}

.billing-order-item p {
  margin: 0 0 10px;
  color: @text-secondary;
  line-height: 1.8;
}

.billing-order-item__meta {
  display: flex;
  flex-wrap: wrap;
  gap: 8px 16px;
  color: @text-secondary;
  font-size: @font-size-xs;
}
</style>
