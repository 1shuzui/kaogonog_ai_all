<template>
  <div class="support-desk page-container">
    <div class="support-desk__hero card">
      <div class="support-desk__hero-copy">
        <span class="support-desk__eyebrow">{{ userStore.isAdmin ? '反馈后台' : '客服反馈中心' }}</span>
        <h2>{{ userStore.isAdmin ? '本地反馈后台总览' : '提交问题并查看处理状态' }}</h2>
        <p>
          当前为纯前端方案，反馈记录保存在本机浏览器。管理员账号可查看全部记录、
          标记处理状态和删除无效记录。
        </p>
      </div>
      <div class="support-desk__hero-actions">
        <a-button @click="copyWechat">复制客服微信</a-button>
        <a-button type="primary" @click="openForm">提交反馈</a-button>
      </div>
    </div>

    <div class="support-desk__stats">
      <div class="card support-stat">
        <span class="support-stat__label">总反馈数</span>
        <strong>{{ stats.total }}</strong>
      </div>
      <div class="card support-stat">
        <span class="support-stat__label">待处理</span>
        <strong>{{ stats.pending }}</strong>
      </div>
      <div class="card support-stat">
        <span class="support-stat__label">今日新增</span>
        <strong>{{ stats.today }}</strong>
      </div>
      <div class="card support-stat">
        <span class="support-stat__label">{{ userStore.isAdmin ? '已处理' : '我的反馈' }}</span>
        <strong>{{ userStore.isAdmin ? stats.handled : stats.mine }}</strong>
      </div>
    </div>

    <div class="card support-desk__contact">
      <div class="support-contact-card">
        <span class="support-contact-card__label">管理员</span>
        <strong>{{ SUPPORT_CONTACT.adminName }}</strong>
        <p>{{ SUPPORT_CONTACT.serviceScope }}</p>
      </div>
      <div class="support-contact-card">
        <span class="support-contact-card__label">客服微信</span>
        <strong>{{ SUPPORT_CONTACT.wechatId }}</strong>
        <p>服务时间：{{ SUPPORT_CONTACT.workTime }}</p>
      </div>
    </div>

    <div class="card support-desk__filters">
      <div class="support-desk__filters-head">
        <h3>筛选反馈</h3>
        <a-button size="small" @click="resetFilters">重置</a-button>
      </div>
      <div class="support-desk__filters-grid">
        <a-select
          v-model:value="filters.type"
          allow-clear
          placeholder="问题类型"
          :options="feedbackTypeOptions"
        />
        <a-select
          v-model:value="filters.status"
          allow-clear
          placeholder="处理状态"
          :options="statusOptions"
        />
        <a-select
          v-model:value="filters.province"
          allow-clear
          placeholder="省份"
          :options="provinceOptions"
        />
        <a-input
          v-model:value="filters.keyword"
          allow-clear
          placeholder="搜索题号、描述、联系方式"
        />
      </div>
      <div v-if="userStore.isAdmin" class="support-desk__scope">
        <a-radio-group v-model:value="filters.scope" size="small">
          <a-radio-button value="all">全部记录</a-radio-button>
          <a-radio-button value="mine">仅看我提交的</a-radio-button>
        </a-radio-group>
      </div>
    </div>

    <div class="support-desk__records">
      <div class="support-desk__records-head">
        <h3>{{ userStore.isAdmin ? '反馈列表' : '我的反馈记录' }}</h3>
        <span>共 {{ filteredRecords.length }} 条</span>
      </div>

      <div v-if="filteredRecords.length" class="support-desk__record-list">
        <div
          v-for="record in filteredRecords"
          :key="record.id"
          class="card support-desk__record"
        >
          <div class="support-desk__record-top">
            <div class="support-desk__record-tags">
              <a-tag color="blue">{{ record.type }}</a-tag>
              <a-tag v-if="record.province" color="gold">{{ record.province }}</a-tag>
              <a-tag v-if="record.questionId" color="purple">{{ record.questionId }}</a-tag>
              <a-tag :color="record.status === 'handled' ? 'success' : 'processing'">
                {{ getStatusLabel(record.status) }}
              </a-tag>
            </div>
            <span class="support-desk__record-time">{{ formatTime(record.createdAt) }}</span>
          </div>

          <div class="support-desk__record-summary">{{ record.summary }}</div>

          <div class="support-desk__record-meta">
            <span>页面：{{ record.routePath || '未记录' }}</span>
            <span v-if="record.contact">联系方式：{{ record.contact }}</span>
            <span v-if="record.username">提交人：{{ record.username }}</span>
            <span v-if="record.handledAt">处理时间：{{ formatTime(record.handledAt) }}</span>
          </div>

          <div v-if="userStore.isAdmin" class="support-desk__record-actions">
            <a-button
              size="small"
              @click="toggleStatus(record)"
            >
              {{ record.status === 'handled' ? '改回待处理' : '标记已处理' }}
            </a-button>
            <a-popconfirm title="确认删除这条反馈？" @confirm="deleteRecord(record.id)">
              <a-button size="small" danger>删除</a-button>
            </a-popconfirm>
          </div>
        </div>
      </div>

      <a-empty v-else description="暂无符合条件的反馈记录" :image="false" />
    </div>

    <a-modal
      v-model:open="formVisible"
      title="提交客服反馈"
      width="720px"
      @ok="submitFeedback"
      ok-text="提交反馈"
      cancel-text="取消"
    >
      <a-form layout="vertical">
        <a-form-item label="问题类型">
          <a-select v-model:value="form.type" :options="feedbackTypeOptions" placeholder="请选择问题类型" />
        </a-form-item>
        <a-form-item label="题号 / 页面线索">
          <a-input
            v-model:value="form.questionId"
            placeholder="例如：AH-202405-01 / 模拟面试第 2 题 / /pricing"
          />
        </a-form-item>
        <a-form-item label="问题描述">
          <a-textarea
            v-model:value="form.summary"
            :rows="5"
            placeholder="请描述问题现象、出现步骤、你的预期结果。若涉及题库差异，可补充省份、题干和截图说明。"
          />
        </a-form-item>
        <a-form-item label="联系方式">
          <a-input
            v-model:value="form.contact"
            placeholder="可填写微信、手机号或邮箱"
          />
        </a-form-item>
      </a-form>
    </a-modal>
  </div>
</template>

<script setup>
import { computed, onMounted, reactive, ref } from 'vue'
import { useRoute } from 'vue-router'
import { message } from 'ant-design-vue'
import { useUserStore } from '@/stores/user'
import { PROVINCES } from '@/utils/constants'
import {
  FEEDBACK_STATUS_OPTIONS,
  FEEDBACK_TYPES,
  SUPPORT_CONTACT,
  loadFeedbackRecords,
  removeFeedbackRecord,
  saveFeedbackRecord,
  updateFeedbackRecord
} from '@/utils/support'
import { getProvinceLabel } from '@/utils/questionPresentation'

const route = useRoute()
const userStore = useUserStore()

const formVisible = ref(false)
const records = ref([])

const filters = reactive({
  type: undefined,
  status: undefined,
  province: undefined,
  keyword: '',
  scope: 'all'
})

const form = reactive({
  type: FEEDBACK_TYPES[0],
  questionId: '',
  summary: '',
  contact: ''
})

const feedbackTypeOptions = FEEDBACK_TYPES.map((item) => ({ label: item, value: item }))
const statusOptions = FEEDBACK_STATUS_OPTIONS

const provinceOptions = computed(() => {
  const recordNames = Array.from(
    new Set(records.value.map((item) => item.province).filter(Boolean))
  )
  const base = PROVINCES.map((item) => item.name)
  return Array.from(new Set([...base, ...recordNames])).map((item) => ({
    label: item,
    value: item
  }))
})

const currentUsername = computed(() => userStore.userInfo?.name || userStore.username || '游客')

const sourceRecords = computed(() => {
  if (userStore.isAdmin && filters.scope === 'all') return records.value
  return records.value.filter((item) => item.username === currentUsername.value)
})

const filteredRecords = computed(() => {
  const keyword = String(filters.keyword || '').trim().toLowerCase()

  return sourceRecords.value.filter((item) => {
    if (filters.type && item.type !== filters.type) return false
    if (filters.status && item.status !== filters.status) return false
    if (filters.province && item.province !== filters.province) return false
    if (!keyword) return true

    return [
      item.questionId,
      item.summary,
      item.contact,
      item.username,
      item.routePath
    ]
      .map((value) => String(value || '').toLowerCase())
      .some((value) => value.includes(keyword))
  })
})

const stats = computed(() => {
  const todayString = new Date().toISOString().slice(0, 10)
  const mine = records.value.filter((item) => item.username === currentUsername.value)

  return {
    total: records.value.length,
    pending: records.value.filter((item) => item.status !== 'handled').length,
    handled: records.value.filter((item) => item.status === 'handled').length,
    today: records.value.filter((item) => String(item.createdAt || '').startsWith(todayString)).length,
    mine: mine.length
  }
})

onMounted(async () => {
  try {
    if (!userStore.provinces.length) {
      await userStore.loadProvinces()
    }
  } catch {
    // ignore province loading failure
  }

  refreshRecords()
})

function refreshRecords() {
  records.value = loadFeedbackRecords()
}

function resetFilters() {
  filters.type = undefined
  filters.status = undefined
  filters.province = undefined
  filters.keyword = ''
  filters.scope = 'all'
}

function resetForm() {
  form.type = FEEDBACK_TYPES[0]
  form.questionId = ''
  form.summary = ''
  form.contact = ''
}

function openForm() {
  formVisible.value = true
}

function getStatusLabel(status) {
  return FEEDBACK_STATUS_OPTIONS.find((item) => item.value === status)?.label || status
}

async function copyWechat() {
  try {
    await navigator.clipboard.writeText(SUPPORT_CONTACT.wechatId)
    message.success('客服微信已复制')
  } catch {
    message.warning('复制失败，请手动记录客服微信')
  }
}

function submitFeedback() {
  if (!form.summary.trim()) {
    message.warning('请先填写问题描述')
    return
  }

  saveFeedbackRecord({
    type: form.type,
    questionId: form.questionId.trim(),
    summary: form.summary.trim(),
    contact: form.contact.trim(),
    routePath: route.fullPath,
    province: getProvinceLabel(userStore.selectedProvince),
    username: currentUsername.value
  })

  refreshRecords()
  formVisible.value = false
  resetForm()
  message.success('反馈已保存')
}

function toggleStatus(record) {
  const nextStatus = record.status === 'handled' ? 'pending' : 'handled'
  updateFeedbackRecord(record.id, { status: nextStatus })
  refreshRecords()
  message.success(nextStatus === 'handled' ? '已标记为已处理' : '已改回待处理')
}

function deleteRecord(recordId) {
  removeFeedbackRecord(recordId)
  refreshRecords()
  message.success('反馈已删除')
}

function formatTime(value = '') {
  const date = value ? new Date(value) : null
  if (!date || Number.isNaN(date.getTime())) return ''
  return `${date.getFullYear()}-${String(date.getMonth() + 1).padStart(2, '0')}-${String(date.getDate()).padStart(2, '0')} ${String(date.getHours()).padStart(2, '0')}:${String(date.getMinutes()).padStart(2, '0')}`
}
</script>

<style lang="less" scoped>
@import '@/styles/variables.less';

.support-desk {
  display: flex;
  flex-direction: column;
  gap: 14px;
}

.support-desk__hero {
  display: flex;
  justify-content: space-between;
  gap: 18px;
  padding: 24px;
  border-radius: 24px;
  background:
    radial-gradient(circle at top right, rgba(255, 255, 255, 0.16), transparent 24%),
    linear-gradient(135deg, #15477a 0%, @primary-color 58%, #5fa0e8 100%);
  color: #fff;
}

.support-desk__eyebrow {
  display: inline-flex;
  align-items: center;
  min-height: 28px;
  padding: 0 12px;
  border-radius: 999px;
  background: rgba(255, 255, 255, 0.14);
  font-size: 12px;
  font-weight: 600;
}

.support-desk__hero h2 {
  margin: 12px 0 10px;
  color: #fff;
  font-size: 32px;
}

.support-desk__hero p {
  margin: 0;
  color: rgba(255, 255, 255, 0.84);
  line-height: 1.8;
}

.support-desk__hero-actions {
  display: flex;
  flex-direction: column;
  gap: 10px;
  min-width: 160px;
}

.support-desk__stats {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 12px;
}

.support-stat {
  padding: 18px 16px;
  border-radius: 18px;
}

.support-stat__label {
  display: block;
  color: @text-secondary;
  font-size: @font-size-xs;
}

.support-stat strong {
  display: block;
  margin-top: 10px;
  color: @text-primary;
  font-size: 34px;
  line-height: 1;
}

.support-desk__contact {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 12px;
  padding: 16px;
}

.support-contact-card {
  padding: 16px;
  border-radius: 16px;
  background: #fafcff;
  border: 1px solid rgba(27, 95, 170, 0.08);
}

.support-contact-card__label {
  display: block;
  color: @text-secondary;
  font-size: @font-size-xs;
}

.support-contact-card strong {
  display: block;
  margin-top: 6px;
  color: @text-primary;
  font-size: @font-size-base;
}

.support-contact-card p {
  margin: 8px 0 0;
  color: @text-secondary;
  line-height: 1.7;
}

.support-desk__filters {
  padding: 18px 16px;
}

.support-desk__filters-head,
.support-desk__records-head {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 12px;
}

.support-desk__filters-head h3,
.support-desk__records-head h3 {
  margin: 0;
  color: @text-primary;
  font-size: @font-size-lg;
}

.support-desk__records-head span,
.support-desk__filters-head span {
  color: @text-secondary;
  font-size: @font-size-xs;
}

.support-desk__filters-grid {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 12px;
  margin-top: 14px;
}

.support-desk__scope {
  margin-top: 14px;
}

.support-desk__records {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.support-desk__record-list {
  display: grid;
  gap: 12px;
}

.support-desk__record {
  padding: 16px;
  border-radius: 18px;
}

.support-desk__record-top {
  display: flex;
  justify-content: space-between;
  gap: 12px;
  align-items: flex-start;
}

.support-desk__record-tags,
.support-desk__record-meta,
.support-desk__record-actions {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  align-items: center;
}

.support-desk__record-time,
.support-desk__record-meta {
  color: @text-secondary;
  font-size: @font-size-xs;
}

.support-desk__record-summary {
  margin-top: 12px;
  color: @text-regular;
  line-height: 1.85;
  white-space: pre-wrap;
}

.support-desk__record-meta {
  margin-top: 10px;
}

.support-desk__record-actions {
  margin-top: 14px;
}

@media (max-width: 992px) {
  .support-desk__stats,
  .support-desk__contact,
  .support-desk__filters-grid {
    grid-template-columns: 1fr 1fr;
  }
}

@media (max-width: 768px) {
  .support-desk__hero,
  .support-desk__record-top,
  .support-desk__filters-head,
  .support-desk__records-head {
    flex-direction: column;
    align-items: stretch;
  }

  .support-desk__hero-actions {
    min-width: 0;
  }
}

@media (max-width: 576px) {
  .support-desk__stats,
  .support-desk__contact,
  .support-desk__filters-grid {
    grid-template-columns: 1fr;
  }

  .support-desk__hero {
    padding: 20px 18px;
  }

  .support-desk__hero h2 {
    font-size: 28px;
  }
}
</style>
