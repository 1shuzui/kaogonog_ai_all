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
        <span>已与后端同步</span>
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
        <div v-if="record.attachments?.length" class="support-record__attachments">
          <a-image
            v-for="item in record.attachments"
            :key="item.storageKey || item.url"
            :src="resolveAttachmentUrl(item.url)"
            :alt="item.filename || '反馈截图'"
            :width="72"
            :height="72"
            class="support-record__attachment"
          />
        </div>
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
      :confirm-loading="submitLoading || attachmentUploading"
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
        <a-form-item label="问题截图">
          <a-upload
            v-model:file-list="attachmentFiles"
            accept="image/jpeg,image/png,image/webp,image/gif"
            list-type="picture-card"
            :before-upload="beforeAttachmentUpload"
            :custom-request="uploadAttachment"
            @remove="removeAttachment"
          >
            <div v-if="attachmentFiles.length < MAX_FEEDBACK_IMAGES" class="support-upload-trigger">
              <PlusOutlined />
              <span>上传截图</span>
            </div>
          </a-upload>
          <div class="support-upload-hint">最多 8 张，单张不超过 5MB，支持 JPG、PNG、WEBP、GIF。</div>
        </a-form-item>
      </a-form>
    </a-modal>
  </div>
</template>

<script setup>
import { computed, onMounted, reactive, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { PlusOutlined } from '@ant-design/icons-vue'
import { message, Upload } from 'ant-design-vue'
import { useUserStore } from '@/stores/user'
import {
  FEEDBACK_STATUS_OPTIONS,
  FEEDBACK_TYPES,
  SUPPORT_CONTACT
} from '@/utils/support'
import { createSupportFeedback, getSupportFeedback, uploadSupportFeedbackImage } from '@/api/support'
import { getProvinceLabel } from '@/utils/questionPresentation'

const MAX_FEEDBACK_IMAGES = 8
const MAX_FEEDBACK_IMAGE_BYTES = 5 * 1024 * 1024
const ALLOWED_FEEDBACK_IMAGE_TYPES = ['image/jpeg', 'image/png', 'image/webp', 'image/gif']

const route = useRoute()
const router = useRouter()
const userStore = useUserStore()

const formVisible = ref(false)
const submitLoading = ref(false)
const attachmentUploading = ref(false)
const attachmentFiles = ref([])
const formAttachments = ref([])
const records = ref([])
const feedbackOptions = FEEDBACK_TYPES.map((item) => ({ value: item, label: item }))

const form = reactive({
  type: FEEDBACK_TYPES[0],
  questionId: '',
  summary: '',
  contact: ''
})

const visibleRecords = computed(() => {
  return records.value.slice(0, userStore.isAdmin ? 12 : 5)
})

onMounted(() => {
  loadRecords()
})

watch(() => userStore.isAdmin, () => {
  loadRecords()
})

function resetForm() {
  form.type = FEEDBACK_TYPES[0]
  form.questionId = ''
  form.summary = ''
  form.contact = ''
  formAttachments.value = []
  attachmentFiles.value = []
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

async function submitFeedback() {
  if (!form.summary.trim()) {
    message.warning('请先填写问题描述')
    return
  }
  if (attachmentUploading.value) {
    message.warning('截图仍在上传，请稍后提交')
    return
  }

  submitLoading.value = true
  try {
    await createSupportFeedback({
      type: form.type,
      questionId: form.questionId.trim(),
      summary: form.summary.trim(),
      contact: form.contact.trim(),
      routePath: route.fullPath,
      province: getProvinceLabel(userStore.selectedProvince),
      attachments: formAttachments.value
    })
    await loadRecords()
    formVisible.value = false
    resetForm()
    message.success('反馈已提交，管理员端可实时查看')
  } catch (error) {
    message.error(error?.normalizedMessage || error?.message || '反馈提交失败')
  } finally {
    submitLoading.value = false
  }
}

function beforeAttachmentUpload(file) {
  if (attachmentFiles.value.length >= MAX_FEEDBACK_IMAGES) {
    message.warning('反馈截图最多上传 8 张')
    return Upload.LIST_IGNORE
  }
  if (!ALLOWED_FEEDBACK_IMAGE_TYPES.includes(file.type)) {
    message.warning('仅支持 JPG、PNG、WEBP、GIF 图片')
    return Upload.LIST_IGNORE
  }
  if (file.size > MAX_FEEDBACK_IMAGE_BYTES) {
    message.warning('单张反馈图片不能超过 5MB')
    return Upload.LIST_IGNORE
  }
  return true
}

async function uploadAttachment({ file, onSuccess, onError }) {
  attachmentUploading.value = true
  try {
    const result = await uploadSupportFeedbackImage(file)
    formAttachments.value = [...formAttachments.value, result]
    attachmentFiles.value = attachmentFiles.value.map((item) => (
      item.uid === file.uid
        ? {
          ...item,
          status: 'done',
          url: resolveAttachmentUrl(result.url),
          response: result
        }
        : item
    ))
    onSuccess?.(result)
  } catch (error) {
    message.error(error?.normalizedMessage || error?.message || '截图上传失败')
    onError?.(error)
  } finally {
    attachmentUploading.value = false
  }
}

function removeAttachment(file) {
  const storageKey = file?.response?.storageKey || file?.storageKey || ''
  formAttachments.value = formAttachments.value.filter((item) => item.storageKey !== storageKey)
  attachmentFiles.value = attachmentFiles.value.filter((item) => item.uid !== file.uid)
  return true
}

function getStatusLabel(status) {
  return FEEDBACK_STATUS_OPTIONS.find((item) => item.value === status)?.label || status
}

function formatTime(value = '') {
  const date = value ? new Date(value) : null
  if (!date || Number.isNaN(date.getTime())) return ''
  return `${date.getFullYear()}-${String(date.getMonth() + 1).padStart(2, '0')}-${String(date.getDate()).padStart(2, '0')} ${String(date.getHours()).padStart(2, '0')}:${String(date.getMinutes()).padStart(2, '0')}`
}

function resolveAttachmentUrl(url = '') {
  const value = String(url || '')
  if (!value || /^https?:\/\//i.test(value)) return value
  const apiBase = import.meta.env.VITE_API_BASE || 'https://xzqianmianyuzhoukeji.com/api'
  if (value.startsWith('/api/')) {
    return `${apiBase.replace(/\/api\/?$/, '')}${value}`
  }
  return `${apiBase.replace(/\/+$/, '')}${value.startsWith('/') ? value : `/${value}`}`
}

async function loadRecords() {
  try {
    const response = await getSupportFeedback({
      current: 1,
      pageSize: userStore.isAdmin ? 12 : 5,
      scope: userStore.isAdmin ? 'all' : 'mine'
    })
    records.value = response.list || []
  } catch {
    records.value = []
  }
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

.support-record__attachments {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  margin: 8px 0;
}

.support-record__attachment {
  width: 72px;
  height: 72px;
  object-fit: cover;
  border-radius: 8px;
  border: 1px solid rgba(27, 95, 170, 0.12);
}

.support-upload-trigger {
  display: inline-flex;
  flex-direction: column;
  align-items: center;
  gap: 6px;
  color: @text-secondary;
  font-size: @font-size-xs;
}

.support-upload-hint {
  margin-top: 8px;
  color: @text-secondary;
  font-size: @font-size-xs;
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
