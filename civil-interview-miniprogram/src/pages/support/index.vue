<!--
这个小程序反馈页收集用户问题，题目纠错和支付异常都从这里留下线索。

@param: 无；页面运行时从 props、路由参数、Pinia 状态和用户点击中拿数据。
@return: 渲染当前业务界面，并把按钮、表单或跳转事件交给既有流程处理。
@raises: 不主动抛业务异常；接口失败、未登录和权限不足由请求层或页面提示承接。
-->
<template>
  <view class="page">
    <button class="support-back-button" @tap="goBack">返回</button>

    <view class="card hero-card">
      <view>
        <text class="page-title">{{ userStore.isAdmin ? '客服反馈后台' : '客服反馈中心' }}</text>
        <text class="page-desc">反馈记录已与后端同步，管理员可查看全站反馈。</text>
      </view>
      <button class="primary-button hero-card__button" @tap="openForm">提交反馈</button>
    </view>

    <view class="stats-row">
      <view class="card stat-item">
        <text class="stat-item__label">总反馈</text>
        <text class="stat-item__value">{{ stats.total || 0 }}</text>
      </view>
      <view class="card stat-item">
        <text class="stat-item__label">待处理</text>
        <text class="stat-item__value">{{ stats.pending || 0 }}</text>
      </view>
      <view class="card stat-item">
        <text class="stat-item__label">今日新增</text>
        <text class="stat-item__value">{{ stats.today || 0 }}</text>
      </view>
    </view>

    <view class="card filter-card">
      <picker :range="feedbackTypeNames" :value="typeIndex" @change="onTypeChange">
        <view class="filter-row">
          <text>问题类型</text>
          <text class="filter-row__value">{{ filters.type || '全部类型' }}</text>
        </view>
      </picker>
      <picker :range="statusNames" :value="statusIndex" @change="onStatusChange">
        <view class="filter-row">
          <text>处理状态</text>
          <text class="filter-row__value">{{ statusLabel(filters.status) }}</text>
        </view>
      </picker>
      <picker :range="provinceNames" :value="provinceIndex" @change="onProvinceChange">
        <view class="filter-row">
          <text>省份</text>
          <text class="filter-row__value">{{ filters.province || '全部省份' }}</text>
        </view>
      </picker>
      <input v-model="filters.keyword" class="field field--mt" placeholder="搜索题号、描述、联系方式" confirm-type="search" @confirm="fetchRecords" />
      <button class="secondary-button field--mt" :loading="loading" @tap="fetchRecords">筛选</button>
      <button v-if="userStore.isAdmin" class="secondary-button field--mt" @tap="toggleScope">
        {{ filters.scope === 'all' ? '切换为仅看我提交的' : '切换为查看全部记录' }}
      </button>
    </view>

    <view v-if="records.length">
      <view v-for="record in records" :key="record.id" class="card record-item">
        <view class="record-item__top">
          <view class="record-item__heading">
            <text class="record-item__type">{{ record.type }}</text>
            <text class="record-item__created">提交于 {{ formatTime(record.createdAt) }}</text>
          </view>
          <text class="record-item__status" :class="`record-item__status--${record.status}`">{{ statusLabel(record.status) }}</text>
        </view>
        <text class="record-item__summary">{{ record.summary }}</text>
        <view v-if="recordAttachments(record).length" class="attachment-grid">
          <image
            v-for="(item, index) in recordAttachments(record)"
            :key="item.storageKey || item.url"
            class="attachment-thumb"
            :src="item.url"
            mode="aspectFill"
            @tap="previewAttachments(recordAttachments(record), index)"
          />
        </view>
        <view class="record-item__status-panel" :class="`record-item__status-panel--${record.status}`">
          <text class="record-item__status-title">{{ feedbackStatusTitle(record) }}</text>
          <text class="record-item__status-desc">{{ feedbackStatusDesc(record) }}</text>
          <text v-if="record.handledAt" class="record-item__status-desc">处理时间：{{ formatTime(record.handledAt) }}</text>
          <text v-if="record.adminNote" class="record-item__status-desc">处理说明：{{ record.adminNote }}</text>
        </view>
        <text class="record-item__meta">省份：{{ record.province || '-' }} ｜ 题号：{{ record.questionId || '-' }}</text>
        <text class="record-item__meta">提交人：{{ record.username || '-' }}</text>
        <text v-if="record.contact" class="record-item__meta">联系方式：{{ record.contact }}</text>

        <view v-if="userStore.isAdmin" class="action-row">
          <button class="secondary-button" @tap="toggleStatus(record)">
            {{ record.status === 'handled' ? '改回待处理' : '标记已处理' }}
          </button>
          <button class="secondary-button danger-button" @tap="deleteRecord(record.id)">删除</button>
        </view>
      </view>
    </view>
    <view v-else class="card">
      <EmptyState title="暂无反馈" desc="提交后会在这里显示处理状态。" />
    </view>

    <view v-if="formVisible" class="modal-mask" catchtouchmove="noop" @tap="closeForm">
      <view class="modal-card" @tap.stop>
        <text class="modal-card__title">提交客服反馈</text>
        <scroll-view scroll-y class="modal-card__body">
          <picker :range="feedbackTypeNames.slice(1)" :value="formTypeIndex" @change="onFormTypeChange">
            <view class="filter-row">
              <text>问题类型</text>
              <text class="filter-row__value">{{ form.type }}</text>
            </view>
          </picker>
          <input v-model="form.questionId" class="field field--mt" placeholder="题号 / 页面线索" />
          <textarea v-model="form.summary" class="field field--mt textarea" placeholder="请描述问题现象、出现步骤、你的预期结果。" />
          <input v-model="form.contact" class="field field--mt" placeholder="联系方式（可选）" />
          <view class="form-attachments field--mt">
            <view class="form-attachments__head">
              <text>问题截图</text>
              <text>{{ form.attachments.length }}/{{ MAX_FEEDBACK_IMAGES }}</text>
            </view>
            <view v-if="form.attachments.length" class="attachment-grid attachment-grid--form">
              <view
                v-for="(item, index) in form.attachments"
                :key="item.storageKey || item.url"
                class="attachment-editor"
              >
                <image
                  class="attachment-thumb"
                  :src="item.url"
                  mode="aspectFill"
                  @tap="previewAttachments(form.attachments, index)"
                />
                <button class="attachment-editor__remove" @tap="removeAttachment(index)">×</button>
              </view>
            </view>
            <button
              v-if="form.attachments.length < MAX_FEEDBACK_IMAGES"
              class="secondary-button attachment-add"
              :loading="imageUploading"
              @tap="chooseAttachments"
            >
              上传截图
            </button>
            <text class="attachment-hint">最多 8 张，单张不超过 5MB，支持 JPG、PNG、WEBP、GIF。</text>
          </view>
        </scroll-view>
        <view class="action-row field--mt modal-card__actions">
          <button class="secondary-button" @tap="closeForm">取消</button>
          <button class="primary-button" :loading="submitLoading" @tap="submitFeedback">提交</button>
        </view>
      </view>
    </view>
  </view>
</template>

<script setup>
import { computed, reactive, ref } from 'vue'
import { onShow } from '@dcloudio/uni-app'
import EmptyState from '../../components/EmptyState.vue'
import {
  createSupportFeedback,
  deleteSupportFeedback,
  getSupportFeedback,
  normalizeSupportAttachment,
  updateSupportFeedback,
  uploadSupportFeedbackImage
} from '../../api/support'
import { useUserStore } from '../../stores/user'
import { PROVINCES } from '../../utils/constants'
import { requireLogin, toast } from '../../utils/navigation'

const MAX_FEEDBACK_IMAGES = 8
const MAX_FEEDBACK_IMAGE_BYTES = 5 * 1024 * 1024
const FEEDBACK_TYPES = [
  '全部类型',
  '题库内容问题',
  '题目标签/分类问题',
  '支付或权益问题',
  '录音/视频异常',
  '评分结果疑问',
  '页面显示问题',
  '其他建议'
]
const STATUS_OPTIONS = [
  { value: '', label: '全部状态' },
  { value: 'pending', label: '待处理' },
  { value: 'handled', label: '已处理' }
]

const userStore = useUserStore()
const loading = ref(false)
const submitLoading = ref(false)
const imageUploading = ref(false)
const formVisible = ref(false)
const records = ref([])
const stats = reactive({
  total: 0,
  pending: 0,
  handled: 0,
  today: 0,
  mine: 0
})

const filters = reactive({
  type: '',
  status: '',
  province: '',
  keyword: '',
  scope: 'mine'
})
const form = reactive({
  type: FEEDBACK_TYPES[1],
  questionId: '',
  summary: '',
  contact: '',
  attachments: []
})

const feedbackTypeNames = FEEDBACK_TYPES
const statusNames = STATUS_OPTIONS.map((item) => item.label)
const provinceNames = computed(() => ['全部省份', ...(userStore.provinces.length ? userStore.provinces : PROVINCES).map((item) => item.name)])
const typeIndex = computed(() => Math.max(0, FEEDBACK_TYPES.findIndex((item) => item === (filters.type || '全部类型'))))
const statusIndex = computed(() => Math.max(0, STATUS_OPTIONS.findIndex((item) => item.value === filters.status)))
const provinceIndex = computed(() => Math.max(0, provinceNames.value.findIndex((item) => item === (filters.province || '全部省份'))))
const formTypeIndex = computed(() => Math.max(0, FEEDBACK_TYPES.slice(1).findIndex((item) => item === form.type)))

onShow(async () => {
  if (!requireLogin()) return
  await userStore.loadUserInfo().catch(() => null)
  await userStore.loadProvinces().catch(() => null)
  if (userStore.isAdmin) filters.scope = 'all'
  await fetchRecords()
})

function statusLabel(value = '') {
  return STATUS_OPTIONS.find((item) => item.value === value)?.label || '全部状态'
}

function feedbackStatusTitle(record = {}) {
  return record.status === 'handled' ? '管理员已处理' : '已提交，等待管理员处理'
}

function feedbackStatusDesc(record = {}) {
  if (record.status === 'handled') {
    return record.adminNote ? '请查看下方处理说明。' : '这条反馈已完成处理，如仍有问题可以继续补充提交。'
  }
  return '管理员处理后，处理状态和说明会在这里同步显示。'
}

function onTypeChange(event) {
  const value = FEEDBACK_TYPES[Number(event.detail.value)] || '全部类型'
  filters.type = value === '全部类型' ? '' : value
}

function onStatusChange(event) {
  filters.status = STATUS_OPTIONS[Number(event.detail.value)]?.value || ''
}

function onProvinceChange(event) {
  const value = provinceNames.value[Number(event.detail.value)] || '全部省份'
  filters.province = value === '全部省份' ? '' : value
}

function onFormTypeChange(event) {
  form.type = FEEDBACK_TYPES.slice(1)[Number(event.detail.value)] || FEEDBACK_TYPES[1]
}

function openForm() {
  formVisible.value = true
}

function closeForm() {
  formVisible.value = false
}

function noop() {}

function resetForm() {
  form.questionId = ''
  form.summary = ''
  form.contact = ''
  form.attachments = []
}

function goBack() {
  const pages = typeof getCurrentPages === 'function' ? getCurrentPages() : []
  if (pages.length > 1) {
    uni.navigateBack()
    return
  }
  uni.switchTab({ url: '/pages/profile/index' })
}

function toggleScope() {
  filters.scope = filters.scope === 'all' ? 'mine' : 'all'
  fetchRecords()
}

async function fetchRecords() {
  loading.value = true
  try {
    const response = await getSupportFeedback({
      current: 1,
      pageSize: 200,
      type: filters.type || undefined,
      status: filters.status || undefined,
      province: filters.province || undefined,
      keyword: filters.keyword || undefined,
      scope: userStore.isAdmin ? filters.scope : 'mine'
    })
    records.value = (response.list || []).map((item) => ({
      ...item,
      attachments: Array.isArray(item.attachments)
        ? item.attachments.map((attachment) => normalizeSupportAttachment(attachment))
        : []
    }))
    Object.assign(stats, response.summary || {})
  } catch (error) {
    toast(error?.message || '反馈记录加载失败')
  } finally {
    loading.value = false
  }
}

async function submitFeedback() {
  if (!form.summary.trim()) {
    toast('请先填写问题描述')
    return
  }
  if (imageUploading.value) {
    toast('截图仍在上传，请稍后提交')
    return
  }
  submitLoading.value = true
  try {
    await createSupportFeedback({
      type: form.type,
      questionId: form.questionId.trim(),
      summary: form.summary.trim(),
      contact: form.contact.trim(),
      routePath: '/pages/support/index',
      province: userStore.selectedProvinceName,
      attachments: form.attachments
    })
    formVisible.value = false
    resetForm()
    await fetchRecords()
    toast('反馈已提交', 'success')
  } catch (error) {
    toast(error?.message || '反馈提交失败')
  } finally {
    submitLoading.value = false
  }
}

function getFileSize(filePath = '') {
  if (!filePath || typeof uni.getFileInfo !== 'function') return Promise.resolve(0)
  return new Promise((resolve) => {
    uni.getFileInfo({
      filePath,
      success(res) {
        resolve(Number(res.size || 0))
      },
      fail() {
        resolve(0)
      }
    })
  })
}

async function chooseAttachments() {
  const remaining = MAX_FEEDBACK_IMAGES - form.attachments.length
  if (remaining <= 0) {
    toast('反馈截图最多上传 8 张')
    return
  }
  uni.chooseImage({
    count: remaining,
    sizeType: ['compressed'],
    sourceType: ['album', 'camera'],
    success: async (res) => {
      const files = res.tempFilePaths || []
      if (!files.length) return
      imageUploading.value = true
      try {
        for (const filePath of files) {
          const size = await getFileSize(filePath)
          if (size > MAX_FEEDBACK_IMAGE_BYTES) {
            toast('单张反馈图片不能超过 5MB')
            continue
          }
          const uploaded = await uploadSupportFeedbackImage(filePath)
          form.attachments = [...form.attachments, uploaded].slice(0, MAX_FEEDBACK_IMAGES)
        }
      } catch (error) {
        toast(error?.message || '截图上传失败')
      } finally {
        imageUploading.value = false
      }
    }
  })
}

function removeAttachment(index) {
  form.attachments = form.attachments.filter((_, itemIndex) => itemIndex !== index)
}

function recordAttachments(record = {}) {
  return Array.isArray(record.attachments) ? record.attachments : []
}

function previewAttachments(items = [], current = 0) {
  const urls = items.map((item) => item.url).filter(Boolean)
  if (!urls.length) return
  uni.previewImage({
    urls,
    current: urls[current] || urls[0]
  })
}

async function toggleStatus(record) {
  const nextStatus = record.status === 'handled' ? 'pending' : 'handled'
  try {
    await updateSupportFeedback(record.id, { status: nextStatus })
    await fetchRecords()
    toast(nextStatus === 'handled' ? '已标记为已处理' : '已改回待处理', 'success')
  } catch (error) {
    toast(error?.message || '状态更新失败')
  }
}

async function deleteRecord(recordId) {
  uni.showModal({
    title: '确认删除这条反馈？',
    content: '删除后将无法恢复。',
    confirmText: '删除',
    confirmColor: '#cf1322',
    success: async (res) => {
      if (!res.confirm) return
      try {
        await deleteSupportFeedback(recordId)
        await fetchRecords()
        toast('反馈已删除', 'success')
      } catch (error) {
        toast(error?.message || '反馈删除失败')
      }
    }
  })
}

function formatTime(value = '') {
  const date = value ? new Date(value) : null
  if (!date || Number.isNaN(date.getTime())) return ''
  return `${date.getFullYear()}-${String(date.getMonth() + 1).padStart(2, '0')}-${String(date.getDate()).padStart(2, '0')} ${String(date.getHours()).padStart(2, '0')}:${String(date.getMinutes()).padStart(2, '0')}`
}
</script>

<style scoped>
.support-back-button {
  width: 160rpx;
  min-height: 64rpx;
  margin-bottom: 18rpx;
  border: 1rpx solid #DCEAF7;
  border-radius: 999rpx;
  background: #ffffff;
  color: #2F7FD6;
  font-size: 26rpx;
  font-weight: 800;
}

.hero-card {
  display: grid;
  grid-template-columns: minmax(0, 1fr) 180rpx;
  gap: 16rpx;
  align-items: start;
}

.hero-card__button {
  min-height: 76rpx;
}

.stats-row {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 16rpx;
}

.stat-item {
  text-align: center;
}

.stat-item__label,
.stat-item__value {
  display: block;
}

.stat-item__label {
  color: #64748B;
  font-size: 22rpx;
}

.stat-item__value {
  margin-top: 10rpx;
  color: #2F7FD6;
  font-size: 34rpx;
  font-weight: 900;
}

.filter-row {
  display: flex;
  justify-content: space-between;
  padding: 18rpx 0;
  border-bottom: 1rpx solid #eef2f6;
  color: #2a3648;
  font-size: 26rpx;
}

.filter-row__value {
  color: #2F7FD6;
  font-weight: 700;
}

.field--mt {
  margin-top: 16rpx;
}

.record-item__top {
  display: grid;
  grid-template-columns: minmax(0, 1fr) auto;
  gap: 16rpx;
  align-items: start;
}

.record-item__type,
.record-item__created,
.record-item__status,
.record-item__summary,
.record-item__meta,
.record-item__status-title,
.record-item__status-desc,
.modal-card__title {
  display: block;
}

.record-item__heading {
  min-width: 0;
}

.record-item__type {
  overflow: hidden;
  color: #2F7FD6;
  font-size: 25rpx;
  font-weight: 800;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.record-item__created {
  margin-top: 6rpx;
  color: #8a97a8;
  font-size: 22rpx;
}

.record-item__status {
  padding: 6rpx 14rpx;
  border-radius: 999rpx;
  background: #fff7e6;
  color: #d48806;
  font-size: 23rpx;
  font-weight: 700;
  white-space: nowrap;
}

.record-item__status--pending {
  background: #fff7e6;
  color: #d48806;
}

.record-item__status--handled {
  background: #f0f8ed;
  color: #389e0d;
}

.record-item__summary {
  margin-top: 10rpx;
  color: #172033;
  font-size: 28rpx;
  line-height: 1.7;
  white-space: pre-wrap;
}

.attachment-grid {
  display: flex;
  flex-wrap: wrap;
  gap: 12rpx;
  margin-top: 14rpx;
}

.attachment-grid--form {
  margin-top: 12rpx;
}

.attachment-thumb {
  width: 132rpx;
  height: 132rpx;
  border: 1rpx solid #d9e5f2;
  border-radius: 12rpx;
  background: #f7f9fc;
}

.attachment-editor {
  position: relative;
  width: 132rpx;
  height: 132rpx;
}

.attachment-editor__remove {
  position: absolute;
  top: -10rpx;
  right: -10rpx;
  width: 42rpx;
  height: 42rpx;
  min-height: 42rpx;
  padding: 0;
  border-radius: 50%;
  background: #cf1322;
  color: #fff;
  font-size: 28rpx;
  line-height: 42rpx;
}

.form-attachments {
  padding: 16rpx;
  border: 1rpx solid #e5edf7;
  border-radius: 16rpx;
  background: #f8fbff;
}

.form-attachments__head {
  display: flex;
  justify-content: space-between;
  color: #2a3648;
  font-size: 25rpx;
  font-weight: 800;
}

.attachment-add {
  margin-top: 14rpx;
}

.attachment-hint {
  display: block;
  margin-top: 10rpx;
  color: #64748B;
  font-size: 22rpx;
  line-height: 1.5;
}

.record-item__status-panel {
  margin-top: 14rpx;
  padding: 16rpx;
  border: 1rpx solid #edf2f7;
  border-radius: 14rpx;
  background: #f7f9fc;
}

.record-item__status-panel--handled {
  border-color: #d7efcf;
  background: #f5fbf2;
}

.record-item__status-title {
  color: #1f2b3d;
  font-size: 25rpx;
  font-weight: 800;
}

.record-item__status-desc {
  margin-top: 6rpx;
  color: #5f6f83;
  font-size: 23rpx;
  line-height: 1.6;
}

.record-item__meta {
  margin-top: 8rpx;
  color: #64748B;
  font-size: 23rpx;
}

.modal-mask {
  position: fixed;
  inset: 0;
  z-index: 1000;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 24rpx;
  background: rgba(0, 0, 0, 0.5);
}

.modal-card {
  width: 100%;
  max-height: calc(100vh - 48rpx);
  padding: 28rpx;
  border-radius: 22rpx;
  background: #ffffff;
  box-shadow: 0 28rpx 72rpx rgba(18, 32, 50, 0.26);
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

.modal-card__body {
  flex: 1;
  height: calc(100vh - 260rpx);
  max-height: calc(100vh - 260rpx);
  min-height: 0;
}

.modal-card__actions {
  margin-top: 20rpx;
}

.modal-card__title {
  margin-bottom: 10rpx;
  color: #172033;
  font-size: 32rpx;
  font-weight: 900;
}

.action-row {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 16rpx;
  margin-top: 18rpx;
}

.action-row button {
  min-height: 72rpx;
}

.action-row.modal-card__actions {
  margin-top: 20rpx;
}

.textarea {
  min-height: 220rpx;
}
</style>
