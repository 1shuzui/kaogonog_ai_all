<template>
  <div class="support-center">
    <div class="support-center__hero">
      <div>
        <span class="support-center__eyebrow">客服与反馈</span>
        <h3>题目报错、题库差异、权益异常都可以从这里提交</h3>
        <p>
          如果题库版本存在差异，建议附上题号、所属省份、截图或完整题干，
          便于管理员核对。
        </p>
      </div>
      <div class="support-center__actions">
        <a-button @click="copyWechat">复制微信号</a-button>
        <a-button type="primary" @click="openForm">提交反馈</a-button>
        <a-button @click="goSupportDesk">查看反馈中心</a-button>
      </div>
    </div>

    <div class="support-center__grid">
      <div class="support-contact">
        <span class="support-contact__label">管理员</span>
        <strong>{{ SUPPORT_CONTACT.adminName }}</strong>
        <span class="support-contact__sub">{{ SUPPORT_CONTACT.serviceScope }}</span>
      </div>
      <div class="support-contact">
        <span class="support-contact__label">客服微信</span>
        <strong>{{ SUPPORT_CONTACT.wechatId }}</strong>
        <span class="support-contact__sub">服务时间：{{ SUPPORT_CONTACT.workTime }}</span>
      </div>
    </div>

    <div v-if="visibleRecords.length" class="support-center__records">
      <div class="support-center__records-head">
        <h4>{{ userStore.isAdmin ? '反馈记录总览' : '我最近的反馈' }}</h4>
        <span>本地保存，仅当前浏览器可见</span>
      </div>
      <div
        v-for="record in visibleRecords"
        :key="record.id"
        class="support-record"
      >
        <div class="support-record__top">
          <a-tag color="blue">{{ record.type }}</a-tag>
          <a-tag v-if="record.province" color="gold">{{ record.province }}</a-tag>
          <a-tag v-if="record.questionId" color="purple">{{ record.questionId }}</a-tag>
          <a-tag :color="record.status === 'handled' ? 'success' : 'processing'">
            {{ getStatusLabel(record.status) }}
          </a-tag>
          <span class="support-record__time">{{ formatTime(record.createdAt) }}</span>
        </div>
        <div class="support-record__summary">{{ record.summary }}</div>
        <div class="support-record__meta">
          <span>页面：{{ record.routePath || '未记录' }}</span>
          <span v-if="record.contact">联系方式：{{ record.contact }}</span>
          <span v-if="record.username">提交人：{{ record.username }}</span>
        </div>
      </div>
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
          <a-select v-model:value="form.type" :options="feedbackOptions" placeholder="请选择问题类型" />
        </a-form-item>
        <a-form-item label="题号 / 页面线索">
          <a-input
            v-model:value="form.questionId"
            placeholder="例如：AH-202405-01 / /pricing / 模拟面试第 2 题"
          />
        </a-form-item>
        <a-form-item label="问题描述">
          <a-textarea
            v-model:value="form.summary"
            :rows="5"
            placeholder="请尽量写清问题现象、出现步骤、你期望的正确结果。若涉及题库版本差异，可补充省份与截图说明。"
          />
        </a-form-item>
        <a-form-item label="联系方式">
          <a-input
            v-model:value="form.contact"
            placeholder="可填写微信、手机号或邮箱，方便管理员回访"
          />
        </a-form-item>
      </a-form>
    </a-modal>
  </div>
</template>

<script setup>
import { computed, reactive, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { message } from 'ant-design-vue'
import { useUserStore } from '@/stores/user'
import {
  FEEDBACK_STATUS_OPTIONS,
  FEEDBACK_TYPES,
  SUPPORT_CONTACT,
  loadFeedbackRecords,
  saveFeedbackRecord
} from '@/utils/support'
import { getProvinceLabel } from '@/utils/questionPresentation'

const route = useRoute()
const router = useRouter()
const userStore = useUserStore()

const formVisible = ref(false)
const records = ref(loadFeedbackRecords())
const feedbackOptions = FEEDBACK_TYPES.map((item) => ({ value: item, label: item }))

const form = reactive({
  type: FEEDBACK_TYPES[0],
  questionId: '',
  summary: '',
  contact: ''
})

const visibleRecords = computed(() => {
  const source = userStore.isAdmin
    ? records.value
    : records.value.filter((item) => item.username === (userStore.userInfo?.name || userStore.username || '游客'))

  return source.slice(0, userStore.isAdmin ? 12 : 5)
})

function resetForm() {
  form.type = FEEDBACK_TYPES[0]
  form.questionId = ''
  form.summary = ''
  form.contact = ''
}

function openForm() {
  formVisible.value = true
}

function goSupportDesk() {
  router.push('/support')
}

async function copyWechat() {
  try {
    await navigator.clipboard.writeText(SUPPORT_CONTACT.wechatId)
    message.success('客服微信号已复制')
  } catch {
    message.warning('复制失败，请手动记录微信号')
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
    username: userStore.userInfo?.name || userStore.username || '游客'
  })

  records.value = loadFeedbackRecords()
  formVisible.value = false
  resetForm()
  message.success('反馈已保存，建议同时通过客服微信补充说明')
}

function getStatusLabel(status) {
  return FEEDBACK_STATUS_OPTIONS.find((item) => item.value === status)?.label || status
}

function formatTime(value = '') {
  const date = value ? new Date(value) : null
  if (!date || Number.isNaN(date.getTime())) return ''
  return `${date.getFullYear()}-${String(date.getMonth() + 1).padStart(2, '0')}-${String(date.getDate()).padStart(2, '0')} ${String(date.getHours()).padStart(2, '0')}:${String(date.getMinutes()).padStart(2, '0')}`
}
</script>

<style lang="less" scoped>
@import '@/styles/variables.less';

.support-center {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.support-center__hero {
  display: flex;
  justify-content: space-between;
  gap: 16px;
  padding: 18px;
  border-radius: 18px;
  background: linear-gradient(135deg, rgba(27, 95, 170, 0.1) 0%, rgba(95, 160, 232, 0.08) 100%);
}

.support-center__hero h3 {
  margin: 8px 0 10px;
  color: @text-primary;
  font-size: @font-size-lg;
}

.support-center__hero p {
  margin: 0;
  color: @text-secondary;
  line-height: 1.8;
}

.support-center__eyebrow {
  display: inline-flex;
  align-items: center;
  min-height: 26px;
  padding: 0 10px;
  border-radius: 999px;
  background: rgba(27, 95, 170, 0.08);
  color: @primary-color;
  font-size: 12px;
  font-weight: 600;
}

.support-center__actions {
  display: flex;
  flex-direction: column;
  gap: 10px;
  min-width: 140px;
}

.support-center__grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 12px;
}

.support-contact {
  display: flex;
  flex-direction: column;
  gap: 6px;
  padding: 16px;
  border-radius: 16px;
  background: #fafcff;
  border: 1px solid rgba(27, 95, 170, 0.08);
}

.support-contact__label {
  color: @text-secondary;
  font-size: @font-size-xs;
}

.support-contact strong {
  color: @text-primary;
  font-size: @font-size-base;
}

.support-contact__sub {
  color: @text-secondary;
  font-size: @font-size-sm;
  line-height: 1.7;
}

.support-center__records-head {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 12px;
  margin-bottom: 10px;
}

.support-center__records-head h4 {
  margin: 0;
  color: @text-primary;
  font-size: @font-size-base;
}

.support-center__records-head span {
  color: @text-secondary;
  font-size: @font-size-xs;
}

.support-record {
  padding: 14px 16px;
  border-radius: 16px;
  border: 1px solid rgba(27, 95, 170, 0.08);
  background: #fff;
  margin-bottom: 10px;
}

.support-record__top,
.support-record__meta {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  align-items: center;
}

.support-record__time,
.support-record__meta {
  color: @text-secondary;
  font-size: @font-size-xs;
}

.support-record__summary {
  margin: 10px 0 8px;
  color: @text-regular;
  line-height: 1.8;
  white-space: pre-wrap;
}

@media (max-width: 768px) {
  .support-center__hero,
  .support-center__records-head {
    flex-direction: column;
    align-items: stretch;
  }

  .support-center__grid {
    grid-template-columns: 1fr;
  }

  .support-center__actions {
    min-width: 0;
  }
}
</style>
