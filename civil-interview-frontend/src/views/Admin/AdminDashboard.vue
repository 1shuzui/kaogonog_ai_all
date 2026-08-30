<!--
PC 管理员数据看板首页，展示系统状态、用户增长/活跃、付费、使用数据和单用户下钻。

系统资源只看近 30 天采样；真实活跃时长从心跳上线后开始累计，历史不会用最后活跃时间回填。
-->
<template>
  <div class="admin-dashboard">
    <section class="admin-dashboard__toolbar">
      <div>
        <span class="admin-dashboard__eyebrow">管理员数据看板</span>
        <h1>运营与系统总览</h1>
      </div>
      <div class="admin-dashboard__actions">
        <a-segmented
          v-model:value="filters.systemRange"
          :options="systemRangeOptions"
          @change="handleSystemRangeChange"
        />
        <a-range-picker
          v-model:value="filters.userRange"
          allow-clear
          @change="loadAll"
        />
        <a-button :loading="loading.overview" @click="loadAll">
          <ReloadOutlined /> 刷新
        </a-button>
      </div>
    </section>

    <a-alert
      v-if="error"
      class="admin-dashboard__alert"
      type="error"
      show-icon
      :message="error"
    />

    <section class="status-strip">
      <div class="status-strip__item">
        <span>后端进程</span>
        <strong>{{ latestSystem.backendStatus || 'unknown' }}</strong>
        <small>PID {{ latestSystem.backendPid || '-' }}</small>
      </div>
      <div class="status-strip__item">
        <span>数据库</span>
        <a-tag :color="latestSystem.dbOk ? 'success' : 'error'">{{ latestSystem.dbOk ? '正常' : '异常' }}</a-tag>
        <small>SELECT 1</small>
      </div>
      <div class="status-strip__item">
        <span>Redis</span>
        <a-tag :color="latestSystem.redisOk ? 'success' : 'warning'">{{ latestSystem.redisOk ? '正常' : '未连通' }}</a-tag>
        <small>Ping</small>
      </div>
      <div class="status-strip__item">
        <span>5xx/异常</span>
        <strong>{{ overview.system?.errorCount || 0 }}</strong>
        <small>{{ formatDateTime(overview.system?.lastErrorAt) }}</small>
      </div>
      <div class="status-strip__item">
        <span>最近采样</span>
        <strong>{{ formatPercent(latestSystem.cpuPercent) }}</strong>
        <small>{{ formatDateTime(latestSystem.bucketStart) }}</small>
      </div>
    </section>

    <section class="kpi-grid">
      <div v-for="item in kpiItems" :key="item.key" class="metric-card">
        <div class="metric-card__icon">
          <component :is="item.icon" />
        </div>
        <div>
          <span>{{ item.label }}</span>
          <strong>{{ item.value }}</strong>
          <small>{{ item.hint }}</small>
        </div>
      </div>
    </section>

    <section class="admin-dashboard__main-grid">
      <div class="dashboard-panel dashboard-panel--wide">
        <div class="panel-head">
          <div>
            <h2>服务器资源</h2>
            <p>系统资源数据最多保留最近 30 天。</p>
          </div>
          <a-range-picker
            v-model:value="filters.systemCustomRange"
            show-time
            @change="handleSystemCustomRangeChange"
          />
        </div>
        <div v-if="loading.overview" class="chart-skeleton">
          <a-skeleton active :paragraph="{ rows: 5 }" />
        </div>
        <a-empty v-else-if="!systemSnapshots.length" :image="false" description="暂无系统采样数据" />
        <div v-else ref="systemChartRef" class="dashboard-chart"></div>
      </div>

      <div class="dashboard-panel">
        <div class="panel-head">
          <div>
            <h2>当前资源</h2>
            <p>最后一次采样值。</p>
          </div>
        </div>
        <div class="resource-list">
          <div v-for="item in resourceItems" :key="item.key" class="resource-row">
            <div>
              <span>{{ item.label }}</span>
              <strong>{{ item.value }}</strong>
            </div>
            <a-progress :percent="item.percent" :show-info="false" :status="item.status" />
          </div>
        </div>
      </div>

      <div class="dashboard-panel dashboard-panel--wide">
        <div class="panel-head">
          <div>
            <h2>用户、活跃与付费趋势</h2>
            <p>用户业务数据支持全历史或任意日期区间。</p>
          </div>
        </div>
        <div v-if="loading.overview" class="chart-skeleton">
          <a-skeleton active :paragraph="{ rows: 5 }" />
        </div>
        <a-empty v-else-if="!trendRows.length" :image="false" description="暂无趋势数据" />
        <div v-else ref="trendChartRef" class="dashboard-chart"></div>
      </div>

      <div class="dashboard-panel">
        <div class="panel-head">
          <div>
            <h2>快捷入口</h2>
            <p>保留原后台能力。</p>
          </div>
        </div>
        <div class="quick-links">
          <button v-for="item in quickLinks" :key="item.path" type="button" @click="router.push(item.path)">
            <component :is="item.icon" />
            <span>{{ item.title }}</span>
            <RightOutlined />
          </button>
        </div>
      </div>
    </section>

    <section class="dashboard-panel users-panel">
      <div class="panel-head panel-head--wrap">
        <div>
          <h2>用户列表</h2>
          <p>默认排除 admin、test*、demo*、wx_test*。</p>
        </div>
        <a-space wrap>
          <a-input-search
            v-model:value="userQuery.keyword"
            allow-clear
            placeholder="搜索用户名、姓名、邮箱"
            style="width: 260px"
            @search="loadUsersFirstPage"
          />
          <a-button :loading="loading.users" @click="loadUsersFirstPage">
            <SearchOutlined /> 查询
          </a-button>
        </a-space>
      </div>

      <a-table
        :columns="userColumns"
        :data-source="users"
        :loading="loading.users"
        :pagination="userPagination"
        row-key="username"
        size="middle"
        @change="handleUserTableChange"
      >
        <template #bodyCell="{ column, record }">
          <template v-if="column.key === 'user'">
            <strong>{{ record.username }}</strong>
            <div class="muted-line">{{ record.fullName || record.email || record.province || '-' }}</div>
          </template>
          <template v-else-if="column.key === 'active'">
            <strong>{{ formatDuration(record.activeSeconds) }}</strong>
            <div class="muted-line">{{ record.activeDays || 0 }} 个活跃日</div>
          </template>
          <template v-else-if="column.key === 'usage'">
            <strong>{{ formatDuration(record.usageSeconds) }}</strong>
            <div class="muted-line">{{ record.records || 0 }} 条记录 / {{ record.billedMinutes || 0 }} 分钟扣量</div>
          </template>
          <template v-else-if="column.key === 'payment'">
            <strong>¥{{ money(record.netAmount) }}</strong>
            <div class="muted-line">{{ record.paidOrders || 0 }} 笔支付</div>
          </template>
          <template v-else-if="column.key === 'time'">
            <div>{{ formatDateTime(record.registeredAt) }}</div>
            <div class="muted-line">活跃 {{ formatDateTime(record.lastActiveAt) }}</div>
          </template>
          <template v-else-if="column.key === 'actions'">
            <a-button type="link" @click="openUserDetail(record.username)">下钻</a-button>
          </template>
        </template>
      </a-table>
    </section>

    <a-drawer
      v-model:open="detailVisible"
      width="860"
      title="单用户详情"
      :destroy-on-close="true"
    >
      <div v-if="detailLoading">
        <a-skeleton active :paragraph="{ rows: 8 }" />
      </div>
      <div v-else-if="userDetail.user" class="user-detail">
        <div class="user-detail__head">
          <div>
            <h2>{{ userDetail.user.username }}</h2>
            <p>{{ userDetail.user.fullName || userDetail.user.email || userDetail.user.province || '未填写资料' }}</p>
          </div>
          <a-space>
            <a-button @click="router.push({ path: '/admin/entitlements', query: { username: userDetail.user.username } })">
              <UserOutlined /> 权益
            </a-button>
            <a-button @click="router.push('/admin/invites')">
              <ShareAltOutlined /> 邀请码
            </a-button>
          </a-space>
        </div>

        <div class="detail-kpis">
          <div v-for="item in detailKpis" :key="item.label">
            <span>{{ item.label }}</span>
            <strong>{{ item.value }}</strong>
          </div>
        </div>

        <a-descriptions bordered size="small" :column="2">
          <a-descriptions-item label="注册时间">{{ formatDateTime(userDetail.user.registeredAt) }}</a-descriptions-item>
          <a-descriptions-item label="最近登录">{{ formatDateTime(userDetail.user.lastLoginAt) }}</a-descriptions-item>
          <a-descriptions-item label="最近活跃">{{ formatDateTime(userDetail.user.lastActiveAt) }}</a-descriptions-item>
          <a-descriptions-item label="省份">{{ userDetail.user.province || '-' }}</a-descriptions-item>
        </a-descriptions>

        <h3>每日使用与活跃</h3>
        <a-table
          :columns="dailyColumns"
          :data-source="userDetail.daily || []"
          :pagination="{ pageSize: 8 }"
          row-key="date"
          size="small"
        />

        <h3>使用记录明细</h3>
        <a-table
          :columns="usageRecordColumns"
          :data-source="userDetail.usageRecords?.list || []"
          :pagination="detailPagination"
          row-key="id"
          size="small"
          @change="handleDetailTableChange"
        >
          <template #bodyCell="{ column, record }">
            <template v-if="column.key === 'duration'">
              {{ formatDuration(record.usageSeconds) }} / {{ record.billedMinutes }} 分钟
            </template>
            <template v-else-if="column.key === 'time'">
              {{ formatDateTime(record.reportedAt || record.createdAt) }}
            </template>
          </template>
        </a-table>
      </div>
      <a-empty v-else :image="false" description="暂无用户详情" />
    </a-drawer>
  </div>
</template>

<script setup>
import { computed, nextTick, onBeforeUnmount, onMounted, reactive, ref, watch } from 'vue'
import { useRouter } from 'vue-router'
import dayjs from 'dayjs'
import {
  AimOutlined,
  ClockCircleOutlined,
  CustomerServiceOutlined,
  DatabaseOutlined,
  DollarOutlined,
  FileSearchOutlined,
  HistoryOutlined,
  KeyOutlined,
  ReloadOutlined,
  RightOutlined,
  SearchOutlined,
  ShareAltOutlined,
  TeamOutlined,
  UndoOutlined,
  UserOutlined
} from '@ant-design/icons-vue'
import echarts from '@/utils/echarts'
import {
  getDashboardOverview,
  getDashboardUserDetail,
  getDashboardUsers
} from '@/api/dashboard'

const router = useRouter()
const systemChartRef = ref(null)
const trendChartRef = ref(null)
let systemChart = null
let trendChart = null

const systemRangeOptions = [
  { label: '1小时', value: '1h' },
  { label: '3小时', value: '3h' },
  { label: '1天', value: '1d' },
  { label: '3天', value: '3d' },
  { label: '7天', value: '7d' },
  { label: '30天', value: '30d' }
]

const filters = reactive({
  systemRange: '1d',
  systemCustomRange: [],
  userRange: [dayjs().subtract(6, 'day'), dayjs()]
})
const userQuery = reactive({
  keyword: '',
  page: 1,
  pageSize: 20,
  total: 0
})
const detailQuery = reactive({
  username: '',
  page: 1,
  pageSize: 10
})
const loading = reactive({
  overview: false,
  users: false
})
const detailLoading = ref(false)
const detailVisible = ref(false)
const error = ref('')
const overview = ref({})
const users = ref([])
const userDetail = ref({})

const quickLinks = [
  { title: '用户权益管理', path: '/admin/entitlements', icon: UserOutlined },
  { title: '权益调整流水', path: '/admin/entitlement-adjustments', icon: HistoryOutlined },
  { title: '余额与退款', path: '/admin/refunds', icon: UndoOutlined },
  { title: '密码重置核验', path: '/admin/password-resets', icon: KeyOutlined },
  { title: '邀请码管理', path: '/admin/invites', icon: ShareAltOutlined },
  { title: '定向入口管理', path: '/admin/targeted', icon: AimOutlined },
  { title: '客服反馈', path: '/support', icon: CustomerServiceOutlined },
  { title: '题库管理', path: '/bank', icon: DatabaseOutlined },
  { title: '题库导入', path: '/bank/import', icon: FileSearchOutlined }
]

const userColumns = [
  { title: '用户', key: 'user', width: 210 },
  { title: '真实活跃', key: 'active', width: 150 },
  { title: '训练使用', key: 'usage', width: 190 },
  { title: '付费', key: 'payment', width: 130 },
  { title: '注册/最近活跃', key: 'time', width: 210 },
  { title: '操作', key: 'actions', width: 90, fixed: 'right' }
]

const dailyColumns = [
  { title: '日期', dataIndex: 'date', width: 120 },
  { title: '使用次数', dataIndex: 'usageRecords', width: 100 },
  { title: '训练时长', customRender: ({ record }) => formatDuration(record.usageSeconds), width: 120 },
  { title: '扣量分钟', dataIndex: 'billedMinutes', width: 100 },
  { title: '活跃时长', customRender: ({ record }) => formatDuration(record.activeSeconds), width: 120 },
  { title: '心跳数', dataIndex: 'heartbeatCount', width: 90 }
]

const usageRecordColumns = [
  { title: '考试 ID', dataIndex: 'examId', width: 120 },
  { title: '题目 ID', dataIndex: 'questionId', width: 120 },
  { title: '类型', dataIndex: 'usageType', width: 100 },
  { title: '时长/扣量', key: 'duration', width: 140 },
  { title: '时间', key: 'time', width: 170 }
]

const latestSystem = computed(() => overview.value?.system?.latest || {})
const systemSnapshots = computed(() => overview.value?.system?.snapshots || [])
const trendRows = computed(() => overview.value?.trend || [])
const userRangeParams = computed(() => {
  const [start, end] = Array.isArray(filters.userRange) ? filters.userRange : []
  return {
    userStartDate: formatDay(start),
    userEndDate: formatDay(end),
    startDate: formatDay(start),
    endDate: formatDay(end)
  }
})

const kpiItems = computed(() => [
  {
    key: 'totalUsers',
    label: '用户总量',
    value: integer(overview.value?.users?.totalUsers),
    hint: `${integer(overview.value?.users?.registrations)} 新注册`,
    icon: TeamOutlined
  },
  {
    key: 'activeUsers',
    label: '活跃人数',
    value: integer(overview.value?.users?.activeUsers),
    hint: formatDuration(overview.value?.users?.activeSeconds),
    icon: ClockCircleOutlined
  },
  {
    key: 'usage',
    label: '训练使用',
    value: formatDuration(overview.value?.usage?.usageSeconds),
    hint: `${integer(overview.value?.usage?.records)} 条使用记录`,
    icon: DatabaseOutlined
  },
  {
    key: 'payment',
    label: '实付净额',
    value: `¥${money(overview.value?.payments?.netAmount)}`,
    hint: `${integer(overview.value?.payments?.paidOrders)} 笔支付 / ${money(overview.value?.payments?.refundedAmount)} 退款`,
    icon: DollarOutlined
  }
])

const resourceItems = computed(() => [
  {
    key: 'cpu',
    label: 'CPU',
    value: formatPercent(latestSystem.value.cpuPercent),
    percent: clampPercent(latestSystem.value.cpuPercent),
    status: progressStatus(latestSystem.value.cpuPercent)
  },
  {
    key: 'memory',
    label: '内存',
    value: `${formatPercent(latestSystem.value.memoryPercent)} · ${integer(latestSystem.value.memoryUsedMb)} / ${integer(latestSystem.value.memoryTotalMb)} MB`,
    percent: clampPercent(latestSystem.value.memoryPercent),
    status: progressStatus(latestSystem.value.memoryPercent)
  },
  {
    key: 'disk',
    label: '磁盘',
    value: `${formatPercent(latestSystem.value.diskPercent)} · ${money(latestSystem.value.diskUsedGb)} / ${money(latestSystem.value.diskTotalGb)} GB`,
    percent: clampPercent(latestSystem.value.diskPercent),
    status: progressStatus(latestSystem.value.diskPercent)
  },
  {
    key: 'load',
    label: '负载',
    value: `${money(latestSystem.value.load1m)} / ${money(latestSystem.value.load5m)} / ${money(latestSystem.value.load15m)}`,
    percent: Math.min(Math.round(Number(latestSystem.value.load1m || 0) * 20), 100),
    status: 'normal'
  }
])

const userPagination = computed(() => ({
  current: userQuery.page,
  pageSize: userQuery.pageSize,
  total: userQuery.total,
  showSizeChanger: true,
  showTotal: (count) => `共 ${count} 个用户`
}))

const detailPagination = computed(() => ({
  current: detailQuery.page,
  pageSize: detailQuery.pageSize,
  total: userDetail.value?.usageRecords?.total || 0,
  showSizeChanger: true,
  showTotal: (count) => `共 ${count} 条记录`
}))

const detailKpis = computed(() => {
  const summary = userDetail.value?.summary || {}
  return [
    { label: '真实活跃', value: formatDuration(summary.activeSeconds) },
    { label: '活跃日', value: `${integer(summary.activeDays)} 天` },
    { label: '训练使用', value: formatDuration(summary.usageSeconds) },
    { label: '使用记录', value: integer(summary.usageRecords) },
    { label: '实付净额', value: `¥${money(summary.netAmount)}` },
    { label: '退款金额', value: `¥${money(summary.refundedAmount)}` }
  ]
})

onMounted(() => {
  loadAll()
  window.addEventListener('resize', resizeCharts)
})

onBeforeUnmount(() => {
  window.removeEventListener('resize', resizeCharts)
  systemChart?.dispose()
  trendChart?.dispose()
})

watch(systemSnapshots, () => {
  nextTick(renderSystemChart)
})

watch(trendRows, () => {
  nextTick(renderTrendChart)
})

async function loadAll() {
  await Promise.all([loadOverview(), loadUsers()])
}

async function loadOverview() {
  loading.overview = true
  error.value = ''
  try {
    const systemCustom = Array.isArray(filters.systemCustomRange) ? filters.systemCustomRange : []
    overview.value = await getDashboardOverview({
      userStartDate: userRangeParams.value.userStartDate || undefined,
      userEndDate: userRangeParams.value.userEndDate || undefined,
      systemRange: systemCustom.length ? undefined : filters.systemRange,
      systemStartAt: toIso(systemCustom[0]) || undefined,
      systemEndAt: toIso(systemCustom[1]) || undefined
    })
  } catch (err) {
    error.value = err?.normalizedMessage || err?.message || '看板数据加载失败'
  } finally {
    loading.overview = false
  }
}

async function loadUsers() {
  loading.users = true
  try {
    const response = await getDashboardUsers({
      keyword: userQuery.keyword || undefined,
      startDate: userRangeParams.value.startDate || undefined,
      endDate: userRangeParams.value.endDate || undefined,
      page: userQuery.page,
      pageSize: userQuery.pageSize
    })
    users.value = Array.isArray(response?.list) ? response.list : []
    userQuery.total = Number(response?.total || 0)
  } catch (err) {
    error.value = err?.normalizedMessage || err?.message || '用户列表加载失败'
  } finally {
    loading.users = false
  }
}

async function loadUsersFirstPage() {
  userQuery.page = 1
  await loadUsers()
}

function handleUserTableChange(pagination) {
  userQuery.page = pagination.current || 1
  userQuery.pageSize = pagination.pageSize || 20
  loadUsers()
}

function handleSystemRangeChange() {
  filters.systemCustomRange = []
  loadOverview()
}

function handleSystemCustomRangeChange() {
  loadOverview()
}

async function openUserDetail(username) {
  detailQuery.username = username
  detailQuery.page = 1
  detailVisible.value = true
  await loadUserDetail()
}

async function loadUserDetail() {
  if (!detailQuery.username) return
  detailLoading.value = true
  try {
    userDetail.value = await getDashboardUserDetail(detailQuery.username, {
      startDate: userRangeParams.value.startDate || undefined,
      endDate: userRangeParams.value.endDate || undefined,
      page: detailQuery.page,
      pageSize: detailQuery.pageSize
    })
  } catch (err) {
    error.value = err?.normalizedMessage || err?.message || '用户详情加载失败'
  } finally {
    detailLoading.value = false
  }
}

function handleDetailTableChange(pagination) {
  detailQuery.page = pagination.current || 1
  detailQuery.pageSize = pagination.pageSize || 10
  loadUserDetail()
}

function renderSystemChart() {
  if (!systemChartRef.value || !systemSnapshots.value.length) return
  systemChart?.dispose()
  systemChart = echarts.init(systemChartRef.value)
  systemChart.setOption({
    color: ['#1B5FAA', '#389E0D', '#D48806', '#7A5AF8'],
    tooltip: { trigger: 'axis' },
    legend: { top: 0, right: 8 },
    grid: { top: 44, left: 44, right: 24, bottom: 38 },
    xAxis: {
      type: 'category',
      boundaryGap: false,
      data: systemSnapshots.value.map((item) => formatChartTime(item.bucketStart))
    },
    yAxis: { type: 'value', min: 0, axisLabel: { formatter: '{value}' } },
    series: [
      { name: 'CPU %', type: 'line', smooth: true, data: systemSnapshots.value.map((item) => number(item.cpuPercent)) },
      { name: '内存 %', type: 'line', smooth: true, data: systemSnapshots.value.map((item) => number(item.memoryPercent)) },
      { name: '磁盘 %', type: 'line', smooth: true, data: systemSnapshots.value.map((item) => number(item.diskPercent)) },
      { name: 'Load 1m', type: 'line', smooth: true, data: systemSnapshots.value.map((item) => number(item.load1m)) }
    ]
  })
}

function renderTrendChart() {
  if (!trendChartRef.value || !trendRows.value.length) return
  trendChart?.dispose()
  trendChart = echarts.init(trendChartRef.value)
  trendChart.setOption({
    color: ['#1B5FAA', '#389E0D', '#D48806', '#7A5AF8'],
    tooltip: { trigger: 'axis' },
    legend: { top: 0, right: 8 },
    grid: { top: 44, left: 44, right: 24, bottom: 38 },
    xAxis: { type: 'category', data: trendRows.value.map((item) => item.date) },
    yAxis: [
      { type: 'value', name: '人数/次数' },
      { type: 'value', name: '金额/小时' }
    ],
    series: [
      { name: '注册数', type: 'bar', data: trendRows.value.map((item) => integer(item.registrations)) },
      { name: '活跃人数', type: 'bar', data: trendRows.value.map((item) => integer(item.activeUsers)) },
      { name: '使用小时', type: 'line', yAxisIndex: 1, smooth: true, data: trendRows.value.map((item) => roundNumber((item.usageSeconds || 0) / 3600)) },
      { name: '实付净额', type: 'line', yAxisIndex: 1, smooth: true, data: trendRows.value.map((item) => number(item.netAmount)) }
    ]
  })
}

function resizeCharts() {
  systemChart?.resize()
  trendChart?.resize()
}

function formatDay(value) {
  if (!value) return ''
  if (typeof value?.format === 'function') return value.format('YYYY-MM-DD')
  const date = new Date(value)
  return Number.isNaN(date.getTime()) ? '' : dayjs(date).format('YYYY-MM-DD')
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
  return dayjs(date).format('YYYY-MM-DD HH:mm')
}

function formatChartTime(value) {
  if (!value) return ''
  const date = new Date(value)
  if (Number.isNaN(date.getTime())) return String(value)
  return dayjs(date).format('MM-DD HH:mm')
}

function number(value) {
  const parsed = Number(value || 0)
  return Number.isFinite(parsed) ? parsed : 0
}

function roundNumber(value) {
  return Math.round(number(value) * 100) / 100
}

function integer(value) {
  return Math.round(number(value))
}

function money(value) {
  return roundNumber(value).toFixed(2)
}

function formatPercent(value) {
  return `${roundNumber(value).toFixed(1)}%`
}

function clampPercent(value) {
  return Math.max(0, Math.min(100, Math.round(number(value))))
}

function progressStatus(value) {
  return number(value) >= 90 ? 'exception' : 'normal'
}

function formatDuration(seconds) {
  const total = Math.max(0, integer(seconds))
  if (total < 60) return `${total} 秒`
  if (total < 3600) return `${Math.round(total / 60)} 分钟`
  return `${roundNumber(total / 3600)} 小时`
}
</script>

<style lang="less" scoped>
@import '@/styles/variables.less';

.admin-dashboard {
  width: 100%;
  max-width: none;
  min-height: calc(100vh - @header-height);
  padding: 18px 24px 28px;
  background: #f4f7fb;
}

.admin-dashboard__toolbar {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 16px;
  margin-bottom: 14px;
}

.admin-dashboard__eyebrow {
  display: inline-flex;
  margin-bottom: 4px;
  color: @primary-color;
  font-size: @font-size-xs;
  font-weight: 700;
}

.admin-dashboard h1 {
  margin: 0;
  color: @text-primary;
  font-size: 26px;
  line-height: 1.2;
}

.admin-dashboard__actions {
  display: flex;
  flex-wrap: wrap;
  justify-content: flex-end;
  gap: 10px;
}

.admin-dashboard__alert {
  margin-bottom: 12px;
}

.status-strip,
.kpi-grid,
.admin-dashboard__main-grid {
  display: grid;
  gap: 12px;
}

.status-strip {
  grid-template-columns: repeat(5, minmax(0, 1fr));
  margin-bottom: 12px;
}

.status-strip__item,
.metric-card,
.dashboard-panel {
  border: 1px solid #dfe8f2;
  border-radius: @border-radius;
  background: #fff;
  box-shadow: 0 2px 8px rgba(22, 41, 69, 0.04);
}

.status-strip__item {
  min-height: 86px;
  padding: 12px;
}

.status-strip__item span,
.metric-card span,
.resource-row span,
.detail-kpis span {
  display: block;
  color: @text-secondary;
  font-size: @font-size-xs;
}

.status-strip__item strong,
.metric-card strong,
.resource-row strong {
  display: block;
  margin-top: 5px;
  color: @text-primary;
  font-size: @font-size-xl;
  line-height: 1.25;
}

.status-strip__item small,
.metric-card small {
  display: block;
  margin-top: 5px;
  color: @text-placeholder;
  font-size: @font-size-xs;
}

.kpi-grid {
  grid-template-columns: repeat(4, minmax(0, 1fr));
  margin-bottom: 12px;
}

.metric-card {
  display: grid;
  grid-template-columns: 42px minmax(0, 1fr);
  gap: 12px;
  align-items: center;
  min-height: 104px;
  padding: 14px;
}

.metric-card__icon {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 42px;
  height: 42px;
  border-radius: @border-radius;
  color: @primary-color;
  background: fade(@primary-color, 10%);
  font-size: 20px;
}

.admin-dashboard__main-grid {
  grid-template-columns: minmax(0, 2fr) minmax(320px, 0.9fr);
  align-items: stretch;
  margin-bottom: 12px;
}

.dashboard-panel {
  min-width: 0;
  padding: 14px;
}

.dashboard-panel--wide {
  min-height: 360px;
}

.panel-head {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 12px;
  margin-bottom: 12px;
}

.panel-head--wrap {
  flex-wrap: wrap;
}

.panel-head h2,
.user-detail h2,
.user-detail h3 {
  margin: 0;
  color: @text-primary;
  font-size: @font-size-lg;
}

.panel-head p,
.user-detail p {
  margin: 3px 0 0;
  color: @text-secondary;
  font-size: @font-size-sm;
}

.dashboard-chart {
  width: 100%;
  height: 292px;
}

.chart-skeleton {
  padding: 24px 8px 0;
}

.resource-list {
  display: grid;
  gap: 16px;
}

.resource-row {
  display: grid;
  gap: 8px;
}

.resource-row strong {
  font-size: @font-size-base;
}

.quick-links {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 8px;
}

.quick-links button {
  display: grid;
  grid-template-columns: 22px minmax(0, 1fr) 16px;
  gap: 8px;
  align-items: center;
  min-height: 48px;
  padding: 0 10px;
  border: 1px solid #dfe8f2;
  border-radius: @border-radius;
  background: #fff;
  color: @text-primary;
  text-align: left;
  cursor: pointer;
}

.quick-links button:hover {
  border-color: fade(@primary-color, 35%);
  color: @primary-color;
}

.quick-links span,
.muted-line {
  min-width: 0;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.users-panel {
  padding: 14px;
}

.muted-line {
  margin-top: 2px;
  color: @text-secondary;
  font-size: @font-size-xs;
}

.user-detail {
  display: grid;
  gap: 16px;
}

.user-detail__head {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 12px;
}

.detail-kpis {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 10px;
}

.detail-kpis div {
  padding: 12px;
  border: 1px solid #dfe8f2;
  border-radius: @border-radius;
  background: #f9fbfe;
}

.detail-kpis strong {
  display: block;
  margin-top: 4px;
  color: @text-primary;
  font-size: @font-size-lg;
}

@media (max-width: 1180px) {
  .status-strip,
  .kpi-grid {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }

  .admin-dashboard__main-grid {
    grid-template-columns: 1fr;
  }
}

@media (max-width: 768px) {
  .admin-dashboard {
    padding: 12px;
  }

  .admin-dashboard__toolbar,
  .user-detail__head {
    flex-direction: column;
  }

  .admin-dashboard__actions {
    width: 100%;
    justify-content: flex-start;
  }

  .status-strip,
  .kpi-grid,
  .detail-kpis {
    grid-template-columns: 1fr;
  }

  .quick-links {
    grid-template-columns: 1fr;
  }
}
</style>
