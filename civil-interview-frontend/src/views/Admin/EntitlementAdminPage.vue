<!--
这个网页给管理员查询用户并调整权益；补发和扣减都必须保留原因，方便售后和财务口径回查。

@param: 无；页面运行时从 props、路由参数、Pinia 状态和用户点击中拿数据。
@return: 渲染当前业务界面，并把按钮、表单或跳转事件交给既有流程处理。
@raises: 不主动抛业务异常；接口失败、未登录和权限不足由请求层或页面提示承接。
-->
<template>
  <div class="entitlement-admin page-container">
    <div class="entitlement-admin__header">
      <a-button type="text" @click="router.push('/admin')">
        <LeftOutlined /> 工作台
      </a-button>
      <div>
        <h2>用户权益管理</h2>
        <p>按用户名查询用户，补发人工权益或扣减指定权益剩余时长。</p>
      </div>
      <a-button @click="router.push('/admin/entitlement-adjustments')">
        <HistoryOutlined /> 调整流水
      </a-button>
    </div>

    <div class="card entitlement-admin__search">
      <a-form layout="inline" @submit.prevent>
        <a-form-item label="用户名">
          <a-input
            v-model:value="filters.username"
            allow-clear
            placeholder="输入用户名、昵称或邮箱"
            @press-enter="searchUsers"
          />
        </a-form-item>
        <a-form-item>
          <a-button type="primary" :loading="userLoading" @click="searchUsers">
            <SearchOutlined /> 查询
          </a-button>
        </a-form-item>
      </a-form>
    </div>

    <div class="entitlement-admin__layout">
      <a-table
        class="card entitlement-admin__users"
        :columns="userColumns"
        :data-source="users"
        :loading="userLoading"
        :pagination="{ pageSize: 8 }"
        row-key="username"
        size="middle"
      >
        <template #bodyCell="{ column, record }">
          <template v-if="column.key === 'user'">
            <strong>{{ record.username }}</strong>
            <div class="entitlement-admin__sub">{{ record.fullName || record.email || '无展示资料' }}</div>
          </template>
          <template v-else-if="column.key === 'summary'">
            <div>剩余 {{ record.remainingMinutes || 0 }} 分钟</div>
            <div class="entitlement-admin__sub">权益 {{ record.entitlementCount || 0 }} 条，付费订单 {{ record.orderSummary?.paidOrders || 0 }} 笔</div>
          </template>
          <template v-else-if="column.key === 'active'">
            <div>{{ formatDateTime(record.lastActiveAt) }}</div>
          </template>
          <template v-else-if="column.key === 'actions'">
            <a-button size="small" type="primary" @click="loadDetail(record.username)">查看</a-button>
          </template>
        </template>
      </a-table>

      <div class="card entitlement-admin__detail">
        <template v-if="detail.user">
          <div class="detail-header">
            <div>
              <span class="entitlement-admin__sub">当前用户</span>
              <h3>{{ detail.user.username }}</h3>
              <p>{{ detail.user.fullName || detail.user.email || '无展示资料' }}</p>
            </div>
            <a-button type="primary" @click="openGrant">
              <PlusOutlined /> 补发权益
            </a-button>
          </div>

          <div class="detail-stats">
            <div>
              <span>总剩余</span>
              <strong>{{ detail.subscriptionSummary?.remainingMinutes || 0 }} 分钟</strong>
            </div>
            <div>
              <span>今日可用</span>
              <strong>{{ detail.subscriptionSummary?.remainingDailyMinutes || 0 }} 分钟</strong>
            </div>
            <div>
              <span>付费订单</span>
              <strong>{{ detail.orderSummary?.paidOrders || 0 }} 笔</strong>
            </div>
          </div>

          <a-table
            class="entitlement-admin__entitlements"
            :columns="entitlementColumns"
            :data-source="detail.entitlements || []"
            :pagination="false"
            row-key="subscriptionId"
            size="small"
          >
            <template #bodyCell="{ column, record }">
              <template v-if="column.key === 'plan'">
                <strong>{{ record.planName }}</strong>
                <div class="entitlement-admin__sub">{{ record.packageCode }}</div>
              </template>
              <template v-else-if="column.key === 'minutes'">
                <div>{{ record.remainingMinutes }} / {{ record.totalMinutes }} 分钟</div>
                <div class="entitlement-admin__sub">已用 {{ record.usedMinutes }}，今日 {{ record.dailyUsedMinutes }}/{{ record.dailyLimitMinutes || '不限' }}</div>
              </template>
              <template v-else-if="column.key === 'period'">
                <div>{{ formatDateTime(record.startAt) }}</div>
                <div class="entitlement-admin__sub">至 {{ formatDateTime(record.endAt) }}</div>
              </template>
              <template v-else-if="column.key === 'status'">
                <a-tag :color="record.status === 'active' ? 'green' : 'default'">{{ record.status }}</a-tag>
              </template>
              <template v-else-if="column.key === 'actions'">
                <a-button
                  size="small"
                  danger
                  :disabled="record.remainingMinutes <= 0"
                  @click="openDeduct(record)"
                >
                  扣减
                </a-button>
              </template>
            </template>
          </a-table>

          <div class="recent-adjustments">
            <div class="section-title">
              <h3>最近调整</h3>
              <a-button type="link" @click="router.push({ path: '/admin/entitlement-adjustments', query: { username: detail.user.username } })">
                查看全部
              </a-button>
            </div>
            <a-empty v-if="!detail.recentAdjustments?.length" description="暂无调整记录" />
            <div v-else class="adjustment-list">
              <div v-for="item in detail.recentAdjustments" :key="item.id" class="adjustment-item">
                <a-tag :color="item.actionType === 'grant' ? 'green' : 'orange'">
                  {{ actionText(item.actionType) }}
                </a-tag>
                <strong>{{ item.minutesDelta > 0 ? '+' : '' }}{{ item.minutesDelta }} 分钟</strong>
                <span>{{ item.reasonType }}</span>
                <span>{{ item.operator }}</span>
                <span>{{ formatDateTime(item.createdAt) }}</span>
              </div>
            </div>
          </div>
        </template>
        <a-empty v-else description="请选择一个用户查看权益" />
      </div>
    </div>

    <a-modal
      v-model:open="grantVisible"
      title="补发人工权益"
      :confirm-loading="submitting"
      @ok="submitGrant"
    >
      <a-form layout="vertical">
        <a-form-item label="补发分钟数" required>
          <a-input-number v-model:value="grantForm.totalMinutes" :min="1" style="width: 100%" />
        </a-form-item>
        <a-form-item label="每日限额，0 表示不限" required>
          <a-input-number v-model:value="grantForm.dailyLimitMinutes" :min="0" style="width: 100%" />
        </a-form-item>
        <a-form-item label="开始时间" required>
          <a-date-picker v-model:value="grantForm.startAt" show-time style="width: 100%" />
        </a-form-item>
        <a-form-item label="到期时间" required>
          <a-date-picker v-model:value="grantForm.endAt" show-time style="width: 100%" />
        </a-form-item>
        <a-form-item label="原因类型" required>
          <a-select v-model:value="grantForm.reasonType">
            <a-select-option v-for="item in reasonTypes" :key="item" :value="item">{{ item }}</a-select-option>
          </a-select>
        </a-form-item>
        <a-form-item label="备注" required>
          <a-textarea v-model:value="grantForm.remark" :rows="3" placeholder="填写补发背景、沟通记录或审批说明" />
        </a-form-item>
      </a-form>
    </a-modal>

    <a-modal
      v-model:open="deductVisible"
      title="扣减指定权益"
      :confirm-loading="submitting"
      @ok="submitDeduct"
    >
      <div v-if="activeEntitlement" class="deduct-target">
        <p>权益：{{ activeEntitlement.planName }}</p>
        <p>当前剩余：{{ activeEntitlement.remainingMinutes }} 分钟</p>
      </div>
      <a-form layout="vertical">
        <a-form-item label="扣减分钟数" required>
          <a-input-number
            v-model:value="deductForm.deductMinutes"
            :min="1"
            :max="activeEntitlement?.remainingMinutes || 1"
            style="width: 100%"
          />
        </a-form-item>
        <a-form-item label="原因类型" required>
          <a-select v-model:value="deductForm.reasonType">
            <a-select-option v-for="item in reasonTypes" :key="item" :value="item">{{ item }}</a-select-option>
          </a-select>
        </a-form-item>
        <a-form-item label="备注" required>
          <a-textarea v-model:value="deductForm.remark" :rows="3" placeholder="填写扣减原因和处理依据" />
        </a-form-item>
      </a-form>
    </a-modal>
  </div>
</template>

<script setup>
import { computed, onMounted, reactive, ref } from 'vue'
import { Modal, message } from 'ant-design-vue'
import { useRoute, useRouter } from 'vue-router'
import { HistoryOutlined, LeftOutlined, PlusOutlined, SearchOutlined } from '@ant-design/icons-vue'
import {
  deductUserEntitlement,
  getAdminUserEntitlements,
  grantUserEntitlement,
  searchAdminUsers
} from '@/api/entitlementAdmin'

const router = useRouter()
const route = useRoute()

const reasonTypes = ['客服补偿', '活动赠送', '测试账号', '退款扣减', '误操作修正', '其他']
const filters = reactive({ username: String(route.query.username || '') })
const users = ref([])
const detail = ref({})
const userLoading = ref(false)
const submitting = ref(false)
const grantVisible = ref(false)
const deductVisible = ref(false)
const activeEntitlement = ref(null)

const grantForm = reactive({
  totalMinutes: null,
  dailyLimitMinutes: null,
  startAt: null,
  endAt: null,
  reasonType: '客服补偿',
  remark: ''
})
const deductForm = reactive({
  deductMinutes: null,
  reasonType: '退款扣减',
  remark: ''
})

const userColumns = [
  { title: '用户', key: 'user', width: 200 },
  { title: '权益摘要', key: 'summary' },
  { title: '最近活跃', key: 'active', width: 160 },
  { title: '操作', key: 'actions', width: 90 }
]

const entitlementColumns = [
  { title: '权益', key: 'plan' },
  { title: '分钟数', key: 'minutes', width: 190 },
  { title: '有效期', key: 'period', width: 180 },
  { title: '状态', key: 'status', width: 90 },
  { title: '操作', key: 'actions', width: 90 }
]

const selectedUsername = computed(() => detail.value?.user?.username || '')

onMounted(async () => {
  await searchUsers()
  if (filters.username) {
    const exact = users.value.find((item) => item.username === filters.username)
    if (exact) await loadDetail(exact.username)
  }
})

async function searchUsers() {
  userLoading.value = true
  try {
    const response = await searchAdminUsers({ username: filters.username || undefined, pageSize: 50 })
    users.value = Array.isArray(response?.list) ? response.list : []
  } finally {
    userLoading.value = false
  }
}

async function loadDetail(username) {
  detail.value = await getAdminUserEntitlements(username)
}

function openGrant() {
  grantForm.totalMinutes = null
  grantForm.dailyLimitMinutes = null
  grantForm.startAt = null
  grantForm.endAt = null
  grantForm.reasonType = '客服补偿'
  grantForm.remark = ''
  grantVisible.value = true
}

function openDeduct(record) {
  activeEntitlement.value = record
  deductForm.deductMinutes = null
  deductForm.reasonType = '退款扣减'
  deductForm.remark = ''
  deductVisible.value = true
}

function validateGrant() {
  if (!selectedUsername.value) return '请先选择用户'
  if (!grantForm.totalMinutes || grantForm.totalMinutes <= 0) return '请填写补发分钟数'
  if (grantForm.dailyLimitMinutes === null || grantForm.dailyLimitMinutes === undefined) return '请填写每日限额'
  if (!grantForm.startAt || !grantForm.endAt) return '请填写开始和到期时间'
  if (!grantForm.reasonType || !grantForm.remark?.trim()) return '请填写原因类型和备注'
  return ''
}

function validateDeduct() {
  if (!selectedUsername.value || !activeEntitlement.value) return '请先选择要扣减的权益'
  if (!deductForm.deductMinutes || deductForm.deductMinutes <= 0) return '请填写扣减分钟数'
  if (deductForm.deductMinutes > activeEntitlement.value.remainingMinutes) return '扣减分钟数不能超过剩余分钟'
  if (!deductForm.reasonType || !deductForm.remark?.trim()) return '请填写原因类型和备注'
  return ''
}

async function confirmIfNeeded(title, content, needed) {
  if (!needed) return true
  return new Promise((resolve) => {
    Modal.confirm({
      title,
      content,
      okText: '确认提交',
      cancelText: '取消',
      onOk: () => resolve(true),
      onCancel: () => resolve(false)
    })
  })
}

async function submitGrant() {
  const error = validateGrant()
  if (error) {
    message.warning(error)
    return
  }
  const confirmed = await confirmIfNeeded(
    '确认大额补发',
    `本次将为 ${selectedUsername.value} 补发 ${grantForm.totalMinutes} 分钟，请确认备注和原因准确。`,
    Number(grantForm.totalMinutes) > 300
  )
  if (!confirmed) return
  submitting.value = true
  try {
    await grantUserEntitlement(selectedUsername.value, {
      totalMinutes: grantForm.totalMinutes,
      dailyLimitMinutes: grantForm.dailyLimitMinutes,
      startAt: toIso(grantForm.startAt),
      endAt: toIso(grantForm.endAt),
      reasonType: grantForm.reasonType,
      remark: grantForm.remark
    })
    message.success('人工权益已补发')
    grantVisible.value = false
    await refreshSelectedUser()
  } finally {
    submitting.value = false
  }
}

async function submitDeduct() {
  const error = validateDeduct()
  if (error) {
    message.warning(error)
    return
  }
  const remaining = Number(activeEntitlement.value.remainingMinutes || 0)
  const ratio = remaining > 0 ? Number(deductForm.deductMinutes || 0) / remaining : 1
  const confirmed = await confirmIfNeeded(
    '确认扣减权益',
    `本次将从 ${activeEntitlement.value.planName} 扣减 ${deductForm.deductMinutes} 分钟，提交后会立即生效。`,
    ratio >= 0.8 || Number(deductForm.deductMinutes) >= remaining
  )
  if (!confirmed) return
  submitting.value = true
  try {
    await deductUserEntitlement(selectedUsername.value, {
      subscriptionId: activeEntitlement.value.subscriptionId,
      deductMinutes: deductForm.deductMinutes,
      reasonType: deductForm.reasonType,
      remark: deductForm.remark
    })
    message.success('权益已扣减')
    deductVisible.value = false
    await refreshSelectedUser()
  } finally {
    submitting.value = false
  }
}

async function refreshSelectedUser() {
  await loadDetail(selectedUsername.value)
  await searchUsers()
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
</script>

<style lang="less" scoped>
@import '@/styles/variables.less';

.entitlement-admin__header {
  display: grid;
  grid-template-columns: auto minmax(0, 1fr) auto;
  gap: 12px;
  align-items: center;
  margin-bottom: 16px;
}

.entitlement-admin__header h2 {
  margin: 0;
  color: @text-primary;
  font-size: @font-size-xl;
}

.entitlement-admin__header p {
  margin: 4px 0 0;
  color: @text-secondary;
}

.entitlement-admin__search {
  padding: 16px;
  margin-bottom: 14px;
}

.entitlement-admin__layout {
  display: grid;
  grid-template-columns: minmax(360px, 0.9fr) minmax(520px, 1.4fr);
  gap: 14px;
  align-items: start;
}

.entitlement-admin__users,
.entitlement-admin__detail {
  padding: 0;
  overflow: hidden;
}

.entitlement-admin__detail {
  padding: 18px;
}

.entitlement-admin__sub {
  color: @text-secondary;
  font-size: @font-size-xs;
}

.detail-header {
  display: flex;
  justify-content: space-between;
  gap: 12px;
  margin-bottom: 14px;
}

.detail-header h3 {
  margin: 4px 0;
  color: @text-primary;
  font-size: @font-size-xl;
}

.detail-header p {
  margin: 0;
  color: @text-secondary;
}

.detail-stats {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 10px;
  margin-bottom: 14px;
}

.detail-stats > div {
  padding: 12px;
  border: 1px solid @border-color;
  border-radius: @border-radius;
  background: @page-bg;
}

.detail-stats span {
  display: block;
  margin-bottom: 4px;
  color: @text-secondary;
  font-size: @font-size-xs;
}

.detail-stats strong {
  color: @text-primary;
}

.entitlement-admin__entitlements {
  margin-bottom: 16px;
}

.section-title {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 8px;
}

.section-title h3 {
  margin: 0;
  color: @text-primary;
  font-size: @font-size-lg;
}

.adjustment-list {
  display: grid;
  gap: 8px;
}

.adjustment-item {
  display: grid;
  grid-template-columns: auto auto minmax(80px, 1fr) auto auto;
  gap: 8px;
  align-items: center;
  padding: 10px;
  border: 1px solid @border-color;
  border-radius: @border-radius;
}

.deduct-target {
  padding: 10px 12px;
  margin-bottom: 12px;
  border-radius: @border-radius;
  background: fade(@primary-color, 8%);
}

.deduct-target p {
  margin: 0 0 4px;
}

@media (max-width: 1180px) {
  .entitlement-admin__layout {
    grid-template-columns: 1fr;
  }
}
</style>
