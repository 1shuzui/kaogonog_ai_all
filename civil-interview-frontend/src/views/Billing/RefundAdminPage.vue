<template>
  <div class="refund-admin page-container">
    <div class="refund-admin__header">
      <a-button type="text" @click="$router.back()">
        <LeftOutlined /> 返回
      </a-button>
      <div>
        <h2>余额与退款</h2>
        <p>按订单剩余可用小时统计退款余额，并通过微信官方小程序虚拟支付退款接口处理。</p>
      </div>
      <a-button type="primary" :loading="loading" @click="loadStats">
        <ReloadOutlined /> 刷新
      </a-button>
    </div>

    <div class="card refund-admin__filters">
      <a-form layout="inline" @submit.prevent>
        <a-form-item label="用户名">
          <a-input v-model:value="filters.username" allow-clear placeholder="可选" />
        </a-form-item>
        <a-form-item label="订单号">
          <a-input v-model:value="filters.orderNo" allow-clear placeholder="可选" />
        </a-form-item>
        <a-form-item>
          <a-button type="primary" :loading="loading" @click="loadStats">
            <SearchOutlined /> 查询
          </a-button>
        </a-form-item>
      </a-form>
    </div>

    <div class="refund-admin__summary">
      <div class="card refund-admin__stat">
        <span>总支付金额</span>
        <strong>¥{{ formatAmount(summary.totalPaidAmount) }}</strong>
      </div>
      <div class="card refund-admin__stat">
        <span>购买小时</span>
        <strong>{{ summary.totalHours || 0 }}</strong>
      </div>
      <div class="card refund-admin__stat">
        <span>已用小时</span>
        <strong>{{ summary.usedHours || 0 }}</strong>
      </div>
      <div class="card refund-admin__stat">
        <span>可退余额</span>
        <strong>¥{{ formatAmount(summary.refundableAmount) }}</strong>
      </div>
    </div>

    <a-alert
      v-if="errorText"
      class="refund-admin__alert"
      type="warning"
      show-icon
      :message="errorText"
    />

    <a-table
      class="card refund-admin__table"
      :columns="columns"
      :data-source="items"
      :loading="loading"
      :pagination="{ pageSize: 8 }"
      row-key="orderNo"
      size="middle"
    >
      <template #bodyCell="{ column, record }">
        <template v-if="column.key === 'orderNo'">
          <div class="refund-admin__order-no">{{ record.orderNo }}</div>
          <div class="refund-admin__sub">{{ record.username }}</div>
          <div class="refund-admin__sub">创建：{{ formatDateTime(record.createdAt) }}</div>
        </template>
        <template v-else-if="column.key === 'package'">
          <strong>{{ getPackageName(record) }}</strong>
          <div class="refund-admin__sub">{{ record.packageCode }}</div>
        </template>
        <template v-else-if="column.key === 'hours'">
          <div>{{ record.usedHours || 0 }} / {{ record.totalHours || 0 }} 小时</div>
          <div class="refund-admin__sub">可退 {{ record.refundableHours || 0 }} 小时</div>
        </template>
        <template v-else-if="column.key === 'amount'">
          <div>支付 ¥{{ formatAmount(record.amount) }}</div>
          <div class="refund-admin__sub">可退 ¥{{ formatAmount(record.refundableAmount) }}</div>
        </template>
        <template v-else-if="column.key === 'time'">
          <div>支付：{{ record.paidAt ? formatDateTime(record.paidAt) : '未支付' }}</div>
          <div v-if="record.refundInfo?.refundedAt" class="refund-admin__sub">
            退款：{{ formatDateTime(record.refundInfo.refundedAt) }}
          </div>
          <div v-else class="refund-admin__sub">创建：{{ formatDateTime(record.createdAt) }}</div>
        </template>
        <template v-else-if="column.key === 'status'">
          <a-tag :color="record.status === 'refunded' ? 'blue' : 'green'">
            {{ record.status === 'refunded' ? '已退款' : '可处理' }}
          </a-tag>
        </template>
        <template v-else-if="column.key === 'actions'">
          <a-button
            size="small"
            type="primary"
            :disabled="record.status === 'refunded' || !record.refundableHours"
            @click="openRefund(record)"
          >
            退款
          </a-button>
        </template>
      </template>
    </a-table>

    <a-modal
      v-model:open="refundVisible"
      title="确认微信虚拟支付退款"
      :confirm-loading="refundSubmitting"
      @ok="submitRefund"
    >
      <div v-if="activeRecord" class="refund-admin__modal">
        <p>订单号：{{ activeRecord.orderNo }}</p>
        <p>用户：{{ activeRecord.username }}</p>
        <p>创建时间：{{ formatDateTime(activeRecord.createdAt) }}</p>
        <p>支付时间：{{ activeRecord.paidAt ? formatDateTime(activeRecord.paidAt) : '未支付' }}</p>
        <p>最多可退：{{ activeRecord.refundableHours }} 小时，¥{{ formatAmount(activeRecord.refundableAmount) }}</p>
        <p class="refund-admin__modal-note">提交后会调用微信官方小程序虚拟支付退款接口，并按比例扣减对应训练权益。</p>
        <a-form layout="vertical">
          <a-form-item label="退款小时数">
            <a-input-number
              v-model:value="refundForm.refundedHours"
              :min="0"
              :max="activeRecord.refundableHours || 0"
              style="width: 100%"
            />
          </a-form-item>
          <a-form-item label="备注">
            <a-textarea v-model:value="refundForm.refundRemark" :rows="3" placeholder="可填写退款原因或处理说明" />
          </a-form-item>
        </a-form>
      </div>
    </a-modal>
  </div>
</template>

<script setup>
import { computed, onMounted, reactive, ref } from 'vue'
import { message } from 'ant-design-vue'
import { LeftOutlined, ReloadOutlined, SearchOutlined } from '@ant-design/icons-vue'
import { applyRefund, getRefundBalanceStats } from '@/api/payment'
import { normalizeBillingCopy } from '@/utils/billing'

const filters = reactive({
  username: '',
  orderNo: ''
})
const loading = ref(false)
const refundSubmitting = ref(false)
const errorText = ref('')
const stats = ref({
  list: [],
  summary: {}
})
const refundVisible = ref(false)
const activeRecord = ref(null)
const refundForm = reactive({
  refundedHours: 0,
  refundRemark: ''
})

const items = computed(() => Array.isArray(stats.value.list) ? stats.value.list : [])
const summary = computed(() => stats.value.summary || {})

const columns = [
  { title: '订单/用户', key: 'orderNo', width: 220 },
  { title: '套餐', key: 'package' },
  { title: '使用情况', key: 'hours', width: 160 },
  { title: '金额', key: 'amount', width: 170 },
  { title: '订单时间', key: 'time', width: 190 },
  { title: '状态', key: 'status', width: 110 },
  { title: '操作', key: 'actions', width: 100 }
]

onMounted(() => {
  loadStats()
})

async function loadStats() {
  loading.value = true
  errorText.value = ''
  try {
    stats.value = await getRefundBalanceStats({
      username: filters.username || undefined,
      orderNo: filters.orderNo || undefined
    })
  } catch (error) {
    errorText.value = error?.normalizedMessage || '退款统计加载失败'
  } finally {
    loading.value = false
  }
}

function openRefund(record) {
  activeRecord.value = record
  refundForm.refundedHours = record.refundableHours || 0
  refundForm.refundRemark = ''
  refundVisible.value = true
}

async function submitRefund() {
  if (!activeRecord.value) return
  refundSubmitting.value = true
  try {
    await applyRefund({
      orderNo: activeRecord.value.orderNo,
      refundedHours: refundForm.refundedHours,
      refundRemark: refundForm.refundRemark
    })
    message.success('微信虚拟支付退款已提交')
    refundVisible.value = false
    await loadStats()
  } finally {
    refundSubmitting.value = false
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

function formatAmount(value) {
  return Number(value || 0).toFixed(2)
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

.refund-admin__header {
  display: grid;
  grid-template-columns: auto minmax(0, 1fr) auto;
  gap: 12px;
  align-items: center;
  margin-bottom: 16px;
}

.refund-admin__header h2 {
  margin: 0;
  color: @text-primary;
  font-size: @font-size-xl;
}

.refund-admin__header p {
  margin: 4px 0 0;
  color: @text-secondary;
  font-size: @font-size-sm;
}

.refund-admin__filters {
  padding: 16px;
  margin-bottom: 14px;
}

.refund-admin__summary {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 12px;
  margin-bottom: 14px;
}

.refund-admin__stat {
  padding: 16px;
}

.refund-admin__stat span {
  display: block;
  color: @text-secondary;
  font-size: @font-size-sm;
}

.refund-admin__stat strong {
  display: block;
  margin-top: 8px;
  color: @primary-color;
  font-size: 24px;
}

.refund-admin__alert {
  margin-bottom: 14px;
}

.refund-admin__table {
  padding: 8px;
}

.refund-admin__order-no {
  color: @text-primary;
  font-weight: 700;
}

.refund-admin__sub {
  margin-top: 2px;
  color: @text-secondary;
  font-size: @font-size-xs;
}

.refund-admin__modal p {
  margin: 0 0 8px;
  color: @text-secondary;
}

.refund-admin__modal-note {
  line-height: 1.7;
}

@media (max-width: 900px) {
  .refund-admin__header,
  .refund-admin__summary {
    grid-template-columns: 1fr;
  }
}
</style>
