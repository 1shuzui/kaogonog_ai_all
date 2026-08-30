<!-- 管理员核验密码重置申请并签发一次性验证码；不保存历史审计列表。 -->
<template>
  <div class="password-reset-admin">
    <section class="page-head">
      <div>
        <span class="page-head__eyebrow">管理员工具</span>
        <h1>密码重置核验</h1>
        <p>核对用户名、账号邮箱与申请联系方式后，再生成验证码并通过已核验渠道发送给用户。</p>
      </div>
      <a-space>
        <a-button @click="router.push('/admin')">返回工作台</a-button>
        <a-button type="primary" :loading="loading" @click="loadRequests">刷新</a-button>
      </a-space>
    </section>

    <a-alert
      class="page-alert"
      type="warning"
      show-icon
      message="申请人填写的联系方式不代表账号归属"
      description="请先和账号邮箱或既有客服资料交叉核验，再点击生成。明文验证码只展示一次；重新生成后旧验证码随即失效。"
    />

    <a-alert v-if="error" class="page-alert" type="error" show-icon :message="error" />

    <a-table
      :columns="columns"
      :data-source="requests"
      :loading="loading"
      :pagination="false"
      row-key="requestId"
    >
      <template #bodyCell="{ column, record }">
        <template v-if="column.key === 'user'">
          <strong>{{ record.username }}</strong>
          <div class="muted-line">账号邮箱：{{ record.accountEmail || '未绑定' }}</div>
        </template>
        <template v-else-if="column.key === 'contact'">
          <span>{{ record.contact || '未填写，请通过既有客服渠道核验' }}</span>
        </template>
        <template v-else-if="column.key === 'status'">
          <a-tag :color="statusColor(record.status)">{{ statusText(record.status) }}</a-tag>
          <div v-if="record.expiresAt" class="muted-line">有效至 {{ formatTime(record.expiresAt) }}</div>
        </template>
        <template v-else-if="column.key === 'requestedAt'">
          {{ formatTime(record.requestedAt) }}
        </template>
        <template v-else-if="column.key === 'action'">
          <a-button
            type="primary"
            size="small"
            :loading="issuingId === record.requestId"
            @click="issueCode(record)"
          >
            核验并生成验证码
          </a-button>
        </template>
      </template>
      <template #emptyText>
        <a-empty :image="false" description="暂无密码重置申请" />
      </template>
    </a-table>

    <a-modal v-model:open="codeVisible" title="验证码已生成" :footer="null" width="440px">
      <div v-if="issued" class="issued-code">
        <p>请发送给用户 <strong>{{ issued.username }}</strong>：</p>
        <a-typography-title :level="2" copyable>{{ issued.code }}</a-typography-title>
        <a-descriptions bordered size="small" :column="1">
          <a-descriptions-item label="申请人填写（未验证）">{{ issued.contact || '未填写' }}</a-descriptions-item>
          <a-descriptions-item label="账号邮箱">{{ issued.accountEmail || '未绑定' }}</a-descriptions-item>
          <a-descriptions-item label="失效时间">{{ formatTime(issued.expiresAt) }}</a-descriptions-item>
        </a-descriptions>
        <a-alert
          class="issued-code__alert"
          type="info"
          show-icon
          message="关闭后不会再次显示明文；需要时可重新签发。"
        />
        <a-button type="primary" block @click="codeVisible = false">我已发送</a-button>
      </div>
    </a-modal>
  </div>
</template>

<script setup>
import { onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { message } from 'ant-design-vue'
import dayjs from 'dayjs'
import {
  getPasswordResetAdminRequests,
  issuePasswordResetCode
} from '@/api/auth'

const router = useRouter()
const loading = ref(false)
const issuingId = ref(0)
const requests = ref([])
const error = ref('')
const codeVisible = ref(false)
const issued = ref(null)

const columns = [
  { title: '账号', key: 'user', width: 220 },
  { title: '申请人填写（未验证）', key: 'contact' },
  { title: '状态', key: 'status', width: 190 },
  { title: '申请时间', key: 'requestedAt', width: 180 },
  { title: '操作', key: 'action', width: 170, fixed: 'right' }
]

function formatTime(value) {
  return value ? dayjs(value).format('YYYY-MM-DD HH:mm:ss') : '-'
}

function statusText(status) {
  return {
    pending: '待管理员核验',
    issued: '验证码已签发',
    verified: '用户已验证',
    locked: '尝试过多，需重新签发',
    expired: '验证码已过期'
  }[status] || status || '待处理'
}

function statusColor(status) {
  return {
    pending: 'orange',
    issued: 'blue',
    verified: 'green',
    locked: 'red',
    expired: 'default'
  }[status] || 'default'
}

async function loadRequests() {
  loading.value = true
  error.value = ''
  try {
    const result = await getPasswordResetAdminRequests()
    requests.value = Array.isArray(result?.list) ? result.list : []
  } catch (requestError) {
    error.value = requestError.normalizedMessage || requestError.response?.data?.detail || '密码重置申请加载失败'
  } finally {
    loading.value = false
  }
}

async function issueCode(record) {
  issuingId.value = record.requestId
  try {
    issued.value = await issuePasswordResetCode(record.requestId)
    codeVisible.value = true
    message.success('验证码已生成，请核对联系方式后发送')
    await loadRequests()
  } catch (requestError) {
    message.error(requestError.normalizedMessage || requestError.response?.data?.detail || '验证码生成失败')
  } finally {
    issuingId.value = 0
  }
}

onMounted(loadRequests)
</script>

<style lang="less" scoped>
@import '@/styles/variables.less';

.password-reset-admin {
  max-width: 1180px;
  margin: 0 auto;
  padding: 28px 24px 48px;
}

.page-head {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 24px;
  margin-bottom: 20px;

  h1 {
    margin: 4px 0 6px;
  }

  p {
    margin: 0;
    color: @text-secondary;
  }
}

.page-head__eyebrow {
  color: @primary-color;
  font-weight: 600;
}

.page-alert {
  margin-bottom: 18px;
}

.muted-line {
  margin-top: 4px;
  color: @text-secondary;
  font-size: 12px;
}

.issued-code {
  text-align: center;

  :deep(.ant-descriptions) {
    margin: 18px 0;
    text-align: left;
  }
}

.issued-code__alert {
  margin-bottom: 18px;
  text-align: left;
}

@media (max-width: 720px) {
  .password-reset-admin {
    padding: 18px 12px 32px;
  }

  .page-head {
    flex-direction: column;
  }
}
</style>
