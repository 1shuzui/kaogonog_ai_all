<!--
邀请码管理页，维护合作公司、邀请码、用户归因修正和渠道报表。

管理员在这里手工创建邀请码、启停渠道、纠错单个用户来源并导出日期区间报表；普通用户端不展示邀请码归因。
-->
<template>
  <div class="invite-admin page-container">
    <div class="invite-admin__header">
      <a-button type="text" @click="router.push('/admin')">
        <LeftOutlined /> 工作台
      </a-button>
      <div>
        <h2>邀请码管理</h2>
        <p>维护合作公司、邀请码和渠道报表，用户侧来源不可自行修改。</p>
      </div>
      <a-button type="primary" :loading="loading" @click="loadAll">
        <ReloadOutlined /> 刷新
      </a-button>
    </div>

    <div class="invite-admin__layout">
      <div class="card invite-admin__panel">
        <div class="invite-admin__section-head">
          <h3>合作公司</h3>
          <a-button type="primary" size="small" @click="openPartner()">
            <PlusOutlined /> 新增
          </a-button>
        </div>
        <a-table
          :columns="partnerColumns"
          :data-source="partners"
          :loading="loading"
          :pagination="{ pageSize: 6 }"
          row-key="id"
          size="small"
        >
          <template #bodyCell="{ column, record }">
            <template v-if="column.key === 'name'">
              <strong>{{ record.name }}</strong>
              <div class="invite-admin__sub">{{ record.contactName || record.contactPhone || record.contactWechat || '无联系人' }}</div>
            </template>
            <template v-else-if="column.key === 'status'">
              <a-tag :color="record.enabled ? 'green' : 'default'">{{ record.enabled ? '启用' : '停用' }}</a-tag>
            </template>
            <template v-else-if="column.key === 'actions'">
              <a-space>
                <a-button size="small" @click="openPartner(record)">编辑</a-button>
                <a-popconfirm title="确定删除这个合作公司？" @confirm="removePartner(record)">
                  <a-button size="small" danger>删除</a-button>
                </a-popconfirm>
              </a-space>
            </template>
          </template>
        </a-table>
      </div>

      <div class="card invite-admin__panel">
        <div class="invite-admin__section-head">
          <h3>邀请码</h3>
          <a-button type="primary" size="small" :disabled="!partners.length" @click="openCode()">
            <PlusOutlined /> 新增
          </a-button>
        </div>
        <a-table
          :columns="codeColumns"
          :data-source="codes"
          :loading="loading"
          :pagination="{ pageSize: 6 }"
          row-key="id"
          size="small"
        >
          <template #bodyCell="{ column, record }">
            <template v-if="column.key === 'code'">
              <strong>{{ record.code }}</strong>
              <div class="invite-admin__sub">{{ record.remark || '无备注' }}</div>
            </template>
            <template v-else-if="column.key === 'partner'">
              {{ record.partnerName || partnerName(record.partnerId) }}
            </template>
            <template v-else-if="column.key === 'status'">
              <a-tag :color="record.enabled ? 'green' : 'default'">{{ record.enabled ? '启用' : '停用' }}</a-tag>
            </template>
            <template v-else-if="column.key === 'actions'">
              <a-space>
                <a-button size="small" @click="openCode(record)">编辑</a-button>
                <a-popconfirm title="确定删除这个邀请码？" @confirm="removeCode(record)">
                  <a-button size="small" danger>删除</a-button>
                </a-popconfirm>
              </a-space>
            </template>
          </template>
        </a-table>
      </div>
    </div>

    <div class="card invite-admin__correction">
      <div class="invite-admin__section-head">
        <h3>单用户归因修正</h3>
      </div>
      <a-form layout="inline" @submit.prevent>
        <a-form-item label="用户名" required>
          <a-input v-model:value="correctionForm.username" placeholder="输入用户名" />
        </a-form-item>
        <a-form-item label="邀请码" required>
          <a-select
            v-model:value="correctionForm.inviteCode"
            show-search
            placeholder="选择邀请码"
            style="width: 180px"
            :options="codeOptions"
          />
        </a-form-item>
        <a-form-item label="原因" required>
          <a-input v-model:value="correctionForm.reason" placeholder="填写修正原因" style="width: 280px" />
        </a-form-item>
        <a-form-item>
          <a-button type="primary" :loading="submitting" @click="submitCorrection">保存修正</a-button>
        </a-form-item>
      </a-form>
    </div>

    <div class="card invite-admin__report">
      <div class="invite-admin__section-head invite-admin__section-head--report">
        <h3>渠道报表</h3>
        <div class="invite-admin__report-actions">
          <a-button :loading="reportLoading" @click="loadReport">
            <SearchOutlined /> 查询
          </a-button>
          <a-button :loading="exporting" @click="downloadReport">
            <DownloadOutlined /> 导出 CSV
          </a-button>
        </div>
      </div>

      <a-form layout="inline" class="invite-admin__filters" @submit.prevent>
        <a-form-item label="日期区间">
          <a-range-picker v-model:value="reportRange" />
        </a-form-item>
        <a-form-item label="合作公司">
          <a-select v-model:value="reportForm.partnerId" allow-clear style="width: 180px" :options="partnerOptions" />
        </a-form-item>
        <a-form-item label="邀请码">
          <a-select v-model:value="reportForm.codeId" allow-clear style="width: 160px" :options="codeIdOptions" />
        </a-form-item>
      </a-form>

      <div class="invite-admin__summary">
        <div>
          <span>注册数</span>
          <strong>{{ report.totals?.registrations || 0 }}</strong>
        </div>
        <div>
          <span>活跃人数</span>
          <strong>{{ report.totals?.activeUsers || 0 }}</strong>
        </div>
        <div>
          <span>付费订单</span>
          <strong>{{ report.totals?.paidOrders || 0 }}</strong>
        </div>
        <div>
          <span>实付净额</span>
          <strong>¥{{ money(report.totals?.netPaidAmount) }}</strong>
        </div>
      </div>

      <a-tabs>
        <a-tab-pane key="summary" tab="汇总">
          <a-table
            :columns="reportColumns"
            :data-source="report.summary || []"
            :loading="reportLoading"
            :pagination="{ pageSize: 8 }"
            row-key="code"
            size="small"
          />
        </a-tab-pane>
        <a-tab-pane key="daily" tab="日明细">
          <a-table
            :columns="dailyColumns"
            :data-source="report.daily || []"
            :loading="reportLoading"
            :pagination="{ pageSize: 10 }"
            :row-key="row => `${row.date}-${row.code}`"
            size="small"
          />
        </a-tab-pane>
      </a-tabs>
    </div>

    <a-modal
      v-model:open="partnerVisible"
      :title="partnerForm.id ? '编辑合作公司' : '新增合作公司'"
      :confirm-loading="submitting"
      @ok="submitPartner"
    >
      <a-form layout="vertical">
        <a-form-item label="公司名称" required>
          <a-input v-model:value="partnerForm.name" />
        </a-form-item>
        <a-form-item label="状态">
          <a-switch v-model:checked="partnerForm.enabled" checked-children="启用" un-checked-children="停用" />
        </a-form-item>
        <a-form-item label="联系人">
          <a-input v-model:value="partnerForm.contactName" />
        </a-form-item>
        <a-form-item label="联系电话">
          <a-input v-model:value="partnerForm.contactPhone" />
        </a-form-item>
        <a-form-item label="微信">
          <a-input v-model:value="partnerForm.contactWechat" />
        </a-form-item>
        <a-form-item label="备注">
          <a-textarea v-model:value="partnerForm.remark" :rows="3" />
        </a-form-item>
      </a-form>
    </a-modal>

    <a-modal
      v-model:open="codeVisible"
      :title="codeForm.id ? '编辑邀请码' : '新增邀请码'"
      :confirm-loading="submitting"
      @ok="submitCode"
    >
      <a-form layout="vertical">
        <a-form-item label="邀请码" required>
          <a-input v-model:value="codeForm.code" placeholder="3-32 位字母、数字、_ 或 -" />
        </a-form-item>
        <a-form-item label="合作公司" required>
          <a-select v-model:value="codeForm.partnerId" :options="partnerOptions" />
        </a-form-item>
        <a-form-item label="状态">
          <a-switch v-model:checked="codeForm.enabled" checked-children="启用" un-checked-children="停用" />
        </a-form-item>
        <a-form-item label="备注">
          <a-textarea v-model:value="codeForm.remark" :rows="3" />
        </a-form-item>
      </a-form>
    </a-modal>
  </div>
</template>

<script setup>
import { computed, onMounted, reactive, ref } from 'vue'
import dayjs from 'dayjs'
import { message } from 'ant-design-vue'
import { DownloadOutlined, LeftOutlined, PlusOutlined, ReloadOutlined, SearchOutlined } from '@ant-design/icons-vue'
import { useRouter } from 'vue-router'
import {
  correctInviteAttribution,
  createInviteCode,
  createInvitePartner,
  deleteInviteCode,
  deleteInvitePartner,
  exportInviteReport,
  getInviteReport,
  listInviteCodes,
  listInvitePartners,
  updateInviteCode,
  updateInvitePartner
} from '@/api/invite'

const router = useRouter()
const loading = ref(false)
const submitting = ref(false)
const reportLoading = ref(false)
const exporting = ref(false)
const partners = ref([])
const codes = ref([])
const report = ref({ summary: [], daily: [], totals: {} })
const partnerVisible = ref(false)
const codeVisible = ref(false)
const reportRange = ref([dayjs().subtract(6, 'day'), dayjs()])

const partnerForm = reactive(blankPartner())
const codeForm = reactive(blankCode())
const correctionForm = reactive({ username: '', inviteCode: '', reason: '' })
const reportForm = reactive({ partnerId: undefined, codeId: undefined })

const partnerColumns = [
  { title: '公司', key: 'name' },
  { title: '状态', key: 'status', width: 90 },
  { title: '操作', key: 'actions', width: 90 }
]
const codeColumns = [
  { title: '邀请码', key: 'code' },
  { title: '合作公司', key: 'partner', width: 150 },
  { title: '状态', key: 'status', width: 90 },
  { title: '操作', key: 'actions', width: 90 }
]
const reportColumns = [
  { title: '合作公司', dataIndex: 'partnerName', key: 'partnerName' },
  { title: '邀请码', dataIndex: 'code', key: 'code' },
  { title: '注册数', dataIndex: 'registrations', key: 'registrations' },
  { title: '活跃人数', dataIndex: 'activeUsers', key: 'activeUsers' },
  { title: '付费订单', dataIndex: 'paidOrders', key: 'paidOrders' },
  { title: '实付净额', key: 'netPaidAmount', customRender: ({ record }) => `¥${money(record.netPaidAmount)}` }
]
const dailyColumns = [
  { title: '日期', dataIndex: 'date', key: 'date' },
  ...reportColumns
]

const partnerOptions = computed(() => partners.value.map((item) => ({ label: item.name, value: item.id })))
const codeOptions = computed(() => codes.value.map((item) => ({ label: `${item.code} · ${item.partnerName || partnerName(item.partnerId)}`, value: item.code })))
const codeIdOptions = computed(() => codes.value.map((item) => ({ label: item.code, value: item.id })))

onMounted(() => {
  loadAll()
})

function blankPartner() {
  return { id: 0, name: '', enabled: true, remark: '', contactName: '', contactPhone: '', contactWechat: '' }
}

function blankCode() {
  return { id: 0, code: '', partnerId: undefined, enabled: true, remark: '' }
}

function assignForm(target, value) {
  Object.keys(target).forEach((key) => delete target[key])
  Object.assign(target, value)
}

async function loadAll() {
  loading.value = true
  try {
    const [partnerRes, codeRes] = await Promise.all([listInvitePartners(), listInviteCodes()])
    partners.value = Array.isArray(partnerRes?.list) ? partnerRes.list : []
    codes.value = Array.isArray(codeRes?.list) ? codeRes.list : []
  } finally {
    loading.value = false
  }
}

function openPartner(row = null) {
  assignForm(partnerForm, row ? { ...blankPartner(), ...row } : blankPartner())
  partnerVisible.value = true
}

async function submitPartner() {
  if (!partnerForm.name.trim()) {
    message.warning('请填写公司名称')
    return
  }
  submitting.value = true
  try {
    if (partnerForm.id) {
      await updateInvitePartner(partnerForm.id, partnerForm)
    } else {
      await createInvitePartner(partnerForm)
    }
    partnerVisible.value = false
    message.success('已保存')
    await loadAll()
  } finally {
    submitting.value = false
  }
}

async function removePartner(row) {
  submitting.value = true
  try {
    await deleteInvitePartner(row.id)
    message.success('已删除')
    await loadAll()
  } finally {
    submitting.value = false
  }
}

function openCode(row = null) {
  assignForm(codeForm, row ? { ...blankCode(), ...row } : { ...blankCode(), partnerId: partners.value[0]?.id })
  codeVisible.value = true
}

async function submitCode() {
  if (!codeForm.code.trim() || !codeForm.partnerId) {
    message.warning('请填写邀请码并选择合作公司')
    return
  }
  submitting.value = true
  try {
    const payload = { ...codeForm, code: codeForm.code.trim().toUpperCase() }
    if (codeForm.id) {
      await updateInviteCode(codeForm.id, payload)
    } else {
      await createInviteCode(payload)
    }
    codeVisible.value = false
    message.success('已保存')
    await loadAll()
  } finally {
    submitting.value = false
  }
}

async function removeCode(row) {
  submitting.value = true
  try {
    await deleteInviteCode(row.id)
    message.success('已删除')
    await loadAll()
  } finally {
    submitting.value = false
  }
}

async function submitCorrection() {
  if (!correctionForm.username.trim() || !correctionForm.inviteCode || !correctionForm.reason.trim()) {
    message.warning('请填写用户名、邀请码和修正原因')
    return
  }
  submitting.value = true
  try {
    await correctInviteAttribution(correctionForm.username.trim(), {
      inviteCode: correctionForm.inviteCode,
      reason: correctionForm.reason.trim()
    })
    message.success('归因已修正')
    correctionForm.username = ''
    correctionForm.inviteCode = ''
    correctionForm.reason = ''
  } finally {
    submitting.value = false
  }
}

function reportPayload() {
  const start = reportRange.value?.[0] || dayjs().subtract(6, 'day')
  const end = reportRange.value?.[1] || dayjs()
  return {
    startDate: start.format('YYYY-MM-DD'),
    endDate: end.format('YYYY-MM-DD'),
    partnerId: reportForm.partnerId || undefined,
    codeId: reportForm.codeId || undefined
  }
}

async function loadReport() {
  reportLoading.value = true
  try {
    report.value = await getInviteReport(reportPayload())
  } finally {
    reportLoading.value = false
  }
}

async function downloadReport() {
  exporting.value = true
  try {
    const blob = await exportInviteReport(reportPayload())
    const url = URL.createObjectURL(blob)
    const link = document.createElement('a')
    link.href = url
    link.download = 'invite-report.csv'
    link.click()
    URL.revokeObjectURL(url)
  } finally {
    exporting.value = false
  }
}

function partnerName(id) {
  return partners.value.find((item) => item.id === id)?.name || ''
}

function money(value) {
  return Number(value || 0).toFixed(2)
}
</script>

<style lang="less" scoped>
@import '@/styles/variables.less';

.invite-admin__header {
  display: grid;
  grid-template-columns: auto minmax(0, 1fr) auto;
  gap: 14px;
  align-items: center;
  margin-bottom: 18px;
}

.invite-admin__header h2,
.invite-admin__section-head h3 {
  margin: 0;
  color: @text-primary;
}

.invite-admin__header p {
  margin: 6px 0 0;
  color: @text-secondary;
}

.invite-admin__layout {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 14px;
}

.invite-admin__panel,
.invite-admin__correction,
.invite-admin__report {
  padding: 18px;
}

.invite-admin__correction,
.invite-admin__report {
  margin-top: 14px;
}

.invite-admin__section-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  margin-bottom: 14px;
}

.invite-admin__section-head--report {
  align-items: flex-start;
}

.invite-admin__report-actions {
  display: flex;
  gap: 8px;
}

.invite-admin__sub {
  margin-top: 3px;
  color: @text-secondary;
  font-size: @font-size-sm;
}

.invite-admin__filters {
  margin-bottom: 14px;
}

.invite-admin__summary {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 10px;
  margin: 14px 0;
}

.invite-admin__summary > div {
  padding: 14px;
  border: 1px solid @border-color;
  border-radius: @border-radius;
  background: @bg-light-blue;
}

.invite-admin__summary span {
  display: block;
  color: @text-secondary;
  font-size: @font-size-sm;
}

.invite-admin__summary strong {
  display: block;
  margin-top: 6px;
  color: @text-primary;
  font-size: @font-size-xl;
}

@media (max-width: 900px) {
  .invite-admin__header,
  .invite-admin__layout,
  .invite-admin__summary {
    grid-template-columns: 1fr;
  }
}
</style>
