<template>
  <div class="billing-orders page-container">
    <div class="billing-orders__header">
      <a-button type="text" @click="$router.back()">
        <LeftOutlined /> 返回
      </a-button>
      <div>
        <h2>订单记录</h2>
        <p>展示服务器中的微信官方小程序虚拟支付订单与套餐权益状态。</p>
      </div>
      <a-button :loading="loading" @click="loadOrders">
        <ReloadOutlined /> 刷新
      </a-button>
    </div>

    <div class="card billing-orders__summary">
      <span class="billing-orders__eyebrow">当前套餐</span>
      <h3>{{ billingStore.planLabel }}</h3>
      <p>{{ billingStore.planStatusText }}</p>
      <a-button type="primary" @click="$router.push('/pricing')">查看套餐</a-button>
    </div>

    <a-alert
      v-if="errorText"
      class="billing-orders__alert"
      type="warning"
      show-icon
      :message="errorText"
    />

    <a-table
      v-if="orders.length"
      class="card billing-orders__table"
      :columns="columns"
      :data-source="orders"
      :loading="loading"
      :pagination="{ pageSize: 8 }"
      row-key="orderNo"
      size="middle"
    >
      <template #bodyCell="{ column, record }">
        <template v-if="column.key === 'orderNo'">
          <div class="billing-orders__order-no">{{ record.orderNo }}</div>
          <div class="billing-orders__sub">第三方：{{ record.thirdPartyOrderNo || '暂无' }}</div>
        </template>
        <template v-else-if="column.key === 'package'">
          <strong>{{ getPackageName(record) }}</strong>
          <div class="billing-orders__sub">{{ record.packageCode }}</div>
        </template>
        <template v-else-if="column.key === 'amount'">
          ¥{{ formatAmount(record.amount) }}
        </template>
        <template v-else-if="column.key === 'status'">
          <a-tag :color="getStatusColor(record.status)">{{ getStatusText(record.status) }}</a-tag>
        </template>
        <template v-else-if="column.key === 'createdAt'">
          {{ formatDateTime(record.createdAt) }}
        </template>
        <template v-else-if="column.key === 'paidAt'">
          {{ record.paidAt ? formatDateTime(record.paidAt) : '未支付' }}
        </template>
      </template>
    </a-table>

    <EmptyState v-else-if="!loading" text="暂无虚拟支付订单记录，请在微信小程序套餐中心开通后查看。">
      <template #action>
        <a-button type="primary" @click="$router.push('/pricing')">查看套餐</a-button>
      </template>
    </EmptyState>
  </div>
</template>

<script setup>
import { onMounted, ref } from 'vue'
import { LeftOutlined, ReloadOutlined } from '@ant-design/icons-vue'
import { useBillingStore } from '@/stores/billing'
import { getMyPaymentOrders } from '@/api/payment'
import EmptyState from '@/components/common/EmptyState.vue'
import { normalizeBillingCopy } from '@/utils/billing'

const billingStore = useBillingStore()
const loading = ref(false)
const orders = ref([])
const errorText = ref('')

const columns = [
  { title: '订单号', key: 'orderNo', width: 220 },
  { title: '套餐', key: 'package' },
  { title: '金额', key: 'amount', width: 100 },
  { title: '状态', key: 'status', width: 110 },
  { title: '创建时间', key: 'createdAt', width: 170 },
  { title: '支付时间', key: 'paidAt', width: 170 }
]

onMounted(() => {
  loadOrders()
})

async function loadOrders() {
  loading.value = true
  errorText.value = ''
  try {
    const response = await getMyPaymentOrders()
    orders.value = Array.isArray(response?.list) ? response.list : []
  } catch (error) {
    errorText.value = error?.normalizedMessage || '订单记录加载失败'
  } finally {
    loading.value = false
  }
}

function getPackageName(record) {
  if (record.packageCode === 'trial_3h') return '3小时体验包'
  if (record.packageCode === 'monthly_1h_day') return '包月每日1小时'
  if (record.packageCode === 'monthly_2h_day') return '包月每日2小时'
  if (record.packageCode === 'premium_1000') return '高阶包月 1000元档'
  if (record.packageCode === 'premium_2000') return '高阶包月 2000元档'
  return normalizeBillingCopy(record.packageType || record.packageCode || '套餐')
}

function getStatusText(status = '') {
  const value = String(status || '')
  if (value === 'paid') return '已支付'
  if (value === 'pending') return '待支付'
  if (value === 'refunded') return '已退款'
  if (value === 'closed') return '已关闭'
  return value || '未知'
}

function getStatusColor(status = '') {
  const value = String(status || '')
  if (value === 'paid') return 'green'
  if (value === 'pending') return 'gold'
  if (value === 'refunded') return 'blue'
  if (value === 'closed') return 'default'
  return 'default'
}

function formatAmount(amount) {
  return Number(amount || 0).toFixed(2)
}

function formatDateTime(value) {
  if (!value) return '-'
  const date = new Date(value)
  if (Number.isNaN(date.getTime())) return String(value)
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
  display: grid;
  grid-template-columns: auto minmax(0, 1fr) auto;
  gap: 12px;
  align-items: center;
  margin-bottom: 16px;
}

.billing-orders__header h2 {
  margin: 0;
  color: @text-primary;
  font-size: @font-size-xl;
}

.billing-orders__header p {
  margin: 4px 0 0;
  color: @text-secondary;
  font-size: @font-size-sm;
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

.billing-orders__alert {
  margin-bottom: 14px;
}

.billing-orders__table {
  padding: 8px;
}

.billing-orders__order-no {
  color: @text-primary;
  font-weight: 700;
}

.billing-orders__sub {
  margin-top: 2px;
  color: @text-secondary;
  font-size: @font-size-xs;
}

@media (max-width: 768px) {
  .billing-orders__header {
    grid-template-columns: 1fr;
    align-items: stretch;
  }
}
</style>
