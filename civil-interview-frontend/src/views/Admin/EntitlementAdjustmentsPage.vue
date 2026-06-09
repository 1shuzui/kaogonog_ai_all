<!--
这个网页展示管理员人工调整权益的全局流水；售后追账时需要看到每次补发和扣减的前后快照，而不是只看当前余额。

@param: 无；页面运行时从 props、路由参数、Pinia 状态和用户点击中拿数据。
@return: 渲染当前业务界面，并把按钮、表单或跳转事件交给既有流程处理。
@raises: 不主动抛业务异常；接口失败、未登录和权限不足由请求层或页面提示承接。
-->
<template>
  <div class="entitlement-adjustments page-container">
    <div class="entitlement-adjustments__header">
      <a-button type="text" @click="router.push('/admin')">
        <LeftOutlined /> 工作台
      </a-button>
      <div>
        <h2>权益调整流水</h2>
        <p>按用户、动作、操作者和时间核查人工权益调整记录。</p>
      </div>
      <a-button type="primary" :loading="loading" @click="loadAdjustments">
        <ReloadOutlined /> 刷新
      </a-button>
    </div>

    <div class="card entitlement-adjustments__filters">
      <a-form layout="inline" @submit.prevent>
        <a-form-item label="用户名">
          <a-input
            v-model:value="filters.username"
            allow-clear
            placeholder="可选"
            @press-enter="loadFirstPage"
          />
        </a-form-item>
        <a-form-item label="动作">
          <a-select v-model:value="filters.actionType" allow-clear placeholder="全部" style="width: 130px">
            <a-select-option value="grant">补发</a-select-option>
            <a-select-option value="deduct">扣减</a-select-option>
          </a-select>
        </a-form-item>
        <a-form-item label="操作者">
          <a-input
            v-model:value="filters.operator"
            allow-clear
            placeholder="可选"
            @press-enter="loadFirstPage"
          />
        </a-form-item>
        <a-form-item label="时间范围">
          <a-range-picker v-model:value="filters.range" show-time style="width: 340px" />
        </a-form-item>
        <a-form-item>
          <a-button type="primary" :loading="loading" @click="loadFirstPage">
            <SearchOutlined /> 查询
          </a-button>
        </a-form-item>
      </a-form>
    </div>

    <a-table
      class="card entitlement-adjustments__table"
      :columns="columns"
      :data-source="items"
      :loading="loading"
      :pagination="pagination"
      row-key="id"
      size="middle"
      @change="handleTableChange"
    >
      <template #bodyCell="{ column, record }">
        <template v-if="column.key === 'target'">
          <strong>{{ record.targetUsername }}</strong>
          <div class="entitlement-adjustments__sub">权益 ID：{{ record.subscriptionId || '-' }}</div>
          <a-button type="link" size="small" @click="router.push({ path: '/admin/entitlements', query: { username: record.targetUsername } })">
            查看用户权益
          </a-button>
        </template>
        <template v-else-if="column.key === 'action'">
          <a-tag :color="record.actionType === 'grant' ? 'green' : 'orange'">
            {{ actionText(record.actionType) }}
          </a-tag>
          <div :class="['minutes-delta', record.minutesDelta >= 0 ? 'is-plus' : 'is-minus']">
            {{ record.minutesDelta > 0 ? '+' : '' }}{{ record.minutesDelta }} 分钟
          </div>
        </template>
        <template v-else-if="column.key === 'reason'">
          <strong>{{ record.reasonType }}</strong>
          <div class="entitlement-adjustments__remark">{{ record.remark || '-' }}</div>
        </template>
        <template v-else-if="column.key === 'snapshot'">
          <div class="snapshot-line">
            <span>调整前</span>
            <strong>{{ snapshotText(record.beforeSnapshot) }}</strong>
          </div>
          <div class="snapshot-line">
            <span>调整后</span>
            <strong>{{ snapshotText(record.afterSnapshot) }}</strong>
          </div>
        </template>
        <template v-else-if="column.key === 'operator'">
          <div>{{ record.operator || '-' }}</div>
          <div class="entitlement-adjustments__sub">{{ formatDateTime(record.createdAt) }}</div>
        </template>
      </template>
    </a-table>
  </div>
</template>

<script setup>
import { computed, onMounted, reactive, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { LeftOutlined, ReloadOutlined, SearchOutlined } from '@ant-design/icons-vue'
import { listEntitlementAdjustments } from '@/api/entitlementAdmin'

const router = useRouter()
const route = useRoute()

const filters = reactive({
  username: String(route.query.username || ''),
  actionType: undefined,
  operator: '',
  range: []
})
const loading = ref(false)
const page = ref(1)
const pageSize = ref(20)
const total = ref(0)
const items = ref([])

const columns = [
  { title: '用户/权益', key: 'target', width: 210 },
  { title: '动作', key: 'action', width: 130 },
  { title: '原因与备注', key: 'reason' },
  { title: '前后摘要', key: 'snapshot', width: 260 },
  { title: '操作者/时间', key: 'operator', width: 180 }
]

const pagination = computed(() => ({
  current: page.value,
  pageSize: pageSize.value,
  total: total.value,
  showSizeChanger: true,
  showTotal: (count) => `共 ${count} 条`
}))

onMounted(() => {
  loadAdjustments()
})

async function loadFirstPage() {
  page.value = 1
  await loadAdjustments()
}

async function loadAdjustments() {
  loading.value = true
  try {
    const [startAt, endAt] = Array.isArray(filters.range) ? filters.range : []
    const response = await listEntitlementAdjustments({
      username: filters.username || undefined,
      actionType: filters.actionType || undefined,
      operator: filters.operator || undefined,
      startAt: toIso(startAt) || undefined,
      endAt: toIso(endAt) || undefined,
      page: page.value,
      pageSize: pageSize.value
    })
    items.value = Array.isArray(response?.list) ? response.list : []
    total.value = Number(response?.total || 0)
  } finally {
    loading.value = false
  }
}

function handleTableChange(nextPagination) {
  page.value = nextPagination.current || 1
  pageSize.value = nextPagination.pageSize || 20
  loadAdjustments()
}

function toIso(value) {
  if (!value) return ''
  if (typeof value?.toDate === 'function') return value.toDate().toISOString()
  const date = new Date(value)
  return Number.isNaN(date.getTime()) ? '' : date.toISOString()
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

function actionText(type) {
  return type === 'grant' ? '补发' : '扣减'
}

function snapshotText(snapshot) {
  if (!snapshot || typeof snapshot !== 'object' || !Object.keys(snapshot).length) {
    return '无原权益'
  }
  const remaining = Number(snapshot.remainingMinutes || 0)
  const used = Number(snapshot.usedMinutes || 0)
  const totalMinutes = Number(snapshot.totalMinutes || 0)
  const status = snapshot.status || '-'
  return `剩余 ${remaining} / ${totalMinutes} 分钟，已用 ${used}，${status}`
}
</script>

<style lang="less" scoped>
@import '@/styles/variables.less';

.entitlement-adjustments__header {
  display: grid;
  grid-template-columns: auto minmax(0, 1fr) auto;
  gap: 12px;
  align-items: center;
  margin-bottom: 16px;
}

.entitlement-adjustments__header h2 {
  margin: 0;
  color: @text-primary;
  font-size: @font-size-xl;
}

.entitlement-adjustments__header p {
  margin: 4px 0 0;
  color: @text-secondary;
}

.entitlement-adjustments__filters {
  padding: 16px;
  margin-bottom: 14px;
}

.entitlement-adjustments__table {
  padding: 0;
  overflow: hidden;
}

.entitlement-adjustments__sub {
  margin-top: 2px;
  color: @text-secondary;
  font-size: @font-size-xs;
}

.entitlement-adjustments__remark {
  margin-top: 4px;
  color: @text-secondary;
  line-height: 1.5;
  word-break: break-word;
}

.minutes-delta {
  margin-top: 6px;
  font-weight: 700;
}

.minutes-delta.is-plus {
  color: @score-green;
}

.minutes-delta.is-minus {
  color: @score-gold;
}

.snapshot-line {
  display: flex;
  justify-content: space-between;
  gap: 10px;
  padding: 4px 0;
}

.snapshot-line span {
  flex: 0 0 48px;
  color: @text-secondary;
}

.snapshot-line strong {
  min-width: 0;
  color: @text-primary;
  font-weight: 500;
  text-align: right;
}
</style>
