<!--
这个小程序题库页展示筛选入口和题目列表，未登录可以浏览结构，真实练习前再拦登录。

@param: 无；页面运行时从 props、路由参数、Pinia 状态和用户点击中拿数据。
@return: 渲染当前业务界面，并把按钮、表单或跳转事件交给既有流程处理。
@raises: 不主动抛业务异常；接口失败、未登录和权限不足由请求层或页面提示承接。
-->
<template>
  <view class="page page--tab">
    <view class="bank-header">
      <text class="page-title">{{ isAdmin ? '题库管理' : '题库' }}</text>
      <view v-if="isAdmin" class="bank-header__actions">
        <button class="secondary-button" @tap="goImport">批量导入</button>
        <button class="secondary-button" @tap="showDocxModal = true">docx导入</button>
        <button class="primary-button" @tap="goAdd">新增题目</button>
      </view>
    </view>
    <text class="page-desc">按省份和题型筛选真题，快速进入单题练习。</text>

    <view v-if="readonlyMode" class="card access-card">
      <view class="section-head">
        <text class="section-title">题库未开通</text>
      </view>
      <text class="access-card__desc">完整题库、筛选检索和扩展真题需开通套餐后使用。你可以先体验 1 道试用题。</text>
      <view class="access-card__actions">
        <button class="secondary-button" @tap="startTrial">试用 1 题</button>
        <button class="primary-button" @tap="goPricing">开通套餐</button>
      </view>
    </view>

    <view class="card filter-card">
        <picker :range="examCategoryNames" :value="examCategoryIndex" @change="onExamCategoryChange">
          <view class="filter-row">
            <text>考试类型</text>
            <text class="filter-row__value">{{ selectedExamCategoryName }}</text>
          </view>
        </picker>
        <picker :range="provinceNames" :value="provinceIndex" @change="onProvinceChange">
          <view class="filter-row">
            <text>地区</text>
            <text class="filter-row__value">{{ selectedProvinceName }}</text>
          </view>
        </picker>
        <view class="filter-row filter-row--input">
          <text>三级分类</text>
          <input v-model="subcategoryFilter" class="field filter-input" :placeholder="subcategoryPlaceholder" />
        </view>
        <view class="filter-row filter-row--input">
          <text>四级分类</text>
          <input v-model="subcategory2Filter" class="field filter-input" placeholder="四级分类" />
        </view>
        <view class="filter-row filter-row--year" @tap="showYearPicker = true">
          <text>年份</text>
          <text class="filter-row__value">{{ yearLabel }}</text>
        </view>
        <picker :range="dimensionNames" :value="dimensionIndex" @change="onDimensionChange">
          <view class="filter-row">
            <text>题目分类</text>
            <text class="filter-row__value">{{ selectedDimensionName }}</text>
          </view>
        </picker>
        <picker v-if="isAdmin" :range="categoryReviewNames" :value="categoryReviewIndex" @change="onCategoryReviewChange">
          <view class="filter-row">
            <text>分类复核</text>
            <text class="filter-row__value">{{ selectedCategoryReviewName }}</text>
          </view>
        </picker>
        <view v-if="showPositionFilter" class="filter-row--picker">
          <picker :range="positionNames" :value="positionIndex" @change="onPositionChange">
            <view class="filter-row">
              <text>岗位系统</text>
              <text class="filter-row__value">{{ selectedPositionName }}</text>
            </view>
          </picker>
        </view>
        <view class="search-row">
          <input v-model="keyword" class="field search-row__input" placeholder="搜索题干关键词" confirm-type="search" @confirm="onFilterChange" />
          <button class="secondary-button search-row__button" @tap="onFilterChange">搜索</button>
        </view>
        <view class="quick-actions">
          <button class="secondary-button quick-actions__btn" @tap="startRandomPractice">随机练习</button>
        </view>
    </view>

    <template v-if="!readonlyMode">
      <view v-if="bankStore.questions.length">
        <view v-for="q in bankStore.questions" :key="q.id" class="card bank-item" @tap="openDetail(q)">
          <view class="bank-item__header">
            <text v-if="isAdmin && q.categoryReviewStatus === 'needs_review'" class="review-tag review-tag--pending">分类待确认</text>
            <text v-else-if="isAdmin && q.categoryReviewStatus === 'confirmed'" class="review-tag review-tag--confirmed">分类已确认</text>
            <text class="bank-item__points">{{ q.scoringPoints?.length || 0 }} 个采分点</text>
          </view>
          <view class="bank-item__stem">
            <QuestionCard
              :question="q"
              :show-rich-content="true"
              :collapsed-height="224"
              compact
            />
          </view>
          <view v-if="isAdmin" class="bank-item__actions">
            <button class="secondary-button" @tap.stop="goEdit(q)">编辑</button>
            <button class="secondary-button secondary-button--danger" @tap.stop="onDelete(q)">删除</button>
          </view>
        </view>
      </view>
      <view v-else class="card">
        <EmptyState title="暂无题目" desc="换个省份或题型再试试。" />
      </view>

      <view v-if="totalPages > 1" class="pagination">
        <button class="secondary-button pagination__btn" :disabled="bankStore.pagination.current <= 1" @tap="goPage(bankStore.pagination.current - 1)">上一页</button>
        <text class="pagination__info">{{ bankStore.pagination.current }} / {{ totalPages }}</text>
        <button class="secondary-button pagination__btn" :disabled="bankStore.pagination.current >= totalPages" @tap="goPage(bankStore.pagination.current + 1)">下一页</button>
      </view>
    </template>

    <view v-if="showYearPicker" class="year-overlay" @tap="showYearPicker = false">
      <view class="year-modal card" @tap.stop>
        <view class="section-head">
          <text class="section-title">选择年份</text>
          <text class="muted" @tap="showYearPicker = false">完成</text>
        </view>
        <checkbox-group @change="onYearChange">
          <label v-for="opt in yearOptions" :key="opt.value" class="year-checkbox">
            <checkbox :value="opt.value" :checked="opt.checked" />
            <text>{{ opt.value }}</text>
          </label>
        </checkbox-group>
      </view>
    </view>

    <view v-if="showDocxModal" class="year-overlay" @tap="showDocxModal = false">
      <view class="year-modal card" @tap.stop>
        <view class="section-head">
          <text class="section-title">docx 题库导入</text>
          <text class="muted" @tap="showDocxModal = false">取消</text>
        </view>
        <view class="docx-form">
          <text class="docx-form__label">选择省份</text>
          <picker :range="docxProvinceNames" :value="docxProvinceIndex" @change="onDocxProvinceChange">
            <view class="filter-row">
              <text class="filter-row__value">{{ docxProvinceLabel }}</text>
            </view>
          </picker>
          <text class="docx-form__label" style="margin-top: 20rpx">上传 docx 文件</text>
          <button class="secondary-button" style="margin-top: 12rpx" @tap="chooseDocxFile">选择文件</button>
          <text v-if="docxFileName" class="docx-file-name">{{ docxFileName }}</text>
          <button class="primary-button" style="margin-top: 24rpx" :loading="docxImporting" @tap="handleDocxImport">开始导入</button>
          <view v-if="docxResult" class="docx-result">
            <text>导入成功：{{ docxResult.imported }} 题</text>
            <text v-if="docxResult.suites && docxResult.suites.length">套题：{{ docxResult.suites.join('、') }}</text>
          </view>
        </view>
      </view>
    </view>
  </view>
</template>

<script setup>
import { computed, ref } from 'vue'
import { onShow } from '@dcloudio/uni-app'
import EmptyState from '../../components/EmptyState.vue'
import QuestionCard from '../../components/QuestionCard.vue'
import { importDocx } from '../../api/questionBank'
import { useBillingStore } from '../../stores/billing'
import { useQuestionBankStore } from '../../stores/questionBank'
import { useSubscriptionStore } from '../../stores/subscription'
import { useUserStore } from '../../stores/user'
import { hasPremiumAccess } from '../../utils/access'
import { EXAM_CATEGORIES, PROVINCES, QUESTION_CATEGORIES, SUBCATEGORY_LABELS, YEAR_OPTIONS } from '../../utils/constants'
import { JIANGSU_TARGETED_POSITIONS } from '../../utils/jiangsuJobs'
import { hideLoading, hasToken, promptLoginForAction, showLoading, toast } from '../../utils/navigation'

const billingStore = useBillingStore()
const bankStore = useQuestionBankStore()
const subscriptionStore = useSubscriptionStore()
const userStore = useUserStore()
const isAdmin = computed(() => userStore.isAdmin)
const keyword = ref(bankStore.filters.keyword || '')
const selectedProvince = ref(userStore.selectedProvince || 'national')
const examCategoryFilter = ref('')
const selectedDimension = ref('')
const subcategoryFilter = ref('')
const subcategory2Filter = ref('')
const yearFilter = ref([])
const categoryReviewFilter = ref('')
const selectedPosition = ref('')
const showYearPicker = ref(false)
const showDocxModal = ref(false)
const docxImporting = ref(false)
const docxFileName = ref('')
const docxFilePath = ref('')
const docxProvince = ref('national')
const docxResult = ref(null)

const provinceOptions = computed(() => userStore.provinces.length ? userStore.provinces : PROVINCES)
const provinceNames = computed(() => provinceOptions.value.map((item) => item.name))
const provinceIndex = computed(() => Math.max(0, provinceOptions.value.findIndex((item) => item.code === selectedProvince.value)))
const selectedProvinceName = computed(() => provinceOptions.value[provinceIndex.value]?.name || '国考')

const examCategoryOptions = computed(() => [{ code: '', name: '全部考试类型' }, ...EXAM_CATEGORIES])
const examCategoryNames = computed(() => examCategoryOptions.value.map((item) => item.name))
const examCategoryIndex = computed(() => Math.max(0, examCategoryOptions.value.findIndex((item) => item.code === examCategoryFilter.value)))
const selectedExamCategoryName = computed(() => examCategoryOptions.value[examCategoryIndex.value]?.name || '全部考试类型')

const subcategoryPlaceholder = computed(() => {
  if (!examCategoryFilter.value) return '三级分类'
  return SUBCATEGORY_LABELS[examCategoryFilter.value] || '三级分类'
})

const categoryNames = computed(() => QUESTION_CATEGORIES.map((item) => item.name))
const dimensionOptions = computed(() => [{ key: '', name: '全部分类' }, ...QUESTION_CATEGORIES])
const dimensionNames = computed(() => dimensionOptions.value.map((item) => item.name))
const dimensionIndex = computed(() => Math.max(0, dimensionOptions.value.findIndex((item) => item.key === selectedDimension.value)))
const selectedDimensionName = computed(() => dimensionOptions.value[dimensionIndex.value]?.name || '全部分类')

const categoryReviewOptions = computed(() => [
  { value: '', label: '全部复核状态' },
  { value: 'needs_review', label: '分类待确认' },
  { value: 'confirmed', label: '分类已确认' }
])
const categoryReviewNames = computed(() => categoryReviewOptions.value.map((item) => item.label))
const categoryReviewIndex = computed(() => Math.max(0, categoryReviewOptions.value.findIndex((item) => item.value === categoryReviewFilter.value)))
const selectedCategoryReviewName = computed(() => categoryReviewOptions.value[categoryReviewIndex.value]?.label || '全部复核状态')

const showPositionFilter = computed(() => selectedProvince.value === 'jiangsu')
const positionOptions = computed(() => [
  { code: '', name: '全部岗位系统' },
  ...JIANGSU_TARGETED_POSITIONS
])
const positionNames = computed(() => positionOptions.value.map((item) => item.name))
const positionIndex = computed(() => Math.max(0, positionOptions.value.findIndex((item) => item.code === selectedPosition.value)))
const selectedPositionName = computed(() => positionOptions.value[positionIndex.value]?.name || '全部岗位系统')

const yearOptions = computed(() => YEAR_OPTIONS.map((y) => ({ value: y, checked: yearFilter.value.includes(y) })))
const yearLabel = computed(() => yearFilter.value.length ? yearFilter.value.join('、') : '不限年份（可多选）')

const categoryIndex = computed(() => Math.max(0, QUESTION_CATEGORIES.findIndex((item) => item.key === selectedDimension.value)))
const selectedCategoryName = computed(() => QUESTION_CATEGORIES[categoryIndex.value]?.name || '全部题型')

const hasFullAccess = computed(() => hasPremiumAccess(userStore, billingStore, subscriptionStore))
const readonlyMode = computed(() => !hasFullAccess.value)

const totalPages = computed(() => Math.ceil(bankStore.pagination.total / bankStore.pagination.pageSize))

const DOCX_PROVINCES = [
  { code: 'national', name: '全国通用' },
  { code: '山东', name: '山东' }, { code: '江苏', name: '江苏' },
  { code: '浙江', name: '浙江' }, { code: '广东', name: '广东' },
  { code: '安徽', name: '安徽' }, { code: '湖南', name: '湖南' },
  { code: '湖北', name: '湖北' }, { code: '河南', name: '河南' },
  { code: '四川', name: '四川' }, { code: '河北', name: '河北' },
  { code: '福建', name: '福建' }, { code: '辽宁', name: '辽宁' },
  { code: '陕西', name: '陕西' }, { code: '北京', name: '北京' },
  { code: '上海', name: '上海' }
]
const docxProvinceNames = computed(() => DOCX_PROVINCES.map((item) => item.name))
const docxProvinceIndex = computed(() => Math.max(0, DOCX_PROVINCES.findIndex((item) => item.code === docxProvince.value)))
const docxProvinceLabel = computed(() => DOCX_PROVINCES[docxProvinceIndex.value]?.name || '全国通用')

onShow(async () => {
  if (!hasToken()) {
    bankStore.questions = []
    bankStore.pagination.total = 0
    return
  }
  await Promise.allSettled([
    userStore.loadProvinces(),
    userStore.loadUserInfo(),
    subscriptionStore.refresh({ skipErrorHandler: true })
  ])
  selectedProvince.value = userStore.selectedProvince || 'national'
  if (readonlyMode.value) {
    bankStore.questions = []
    bankStore.pagination.total = 0
    return
  }
  if (!bankStore.questions.length) {
    bankStore.setFilters({ province: '', dimension: '', examCategory: '', subcategory: '', subcategory2: '', year: '', position: '', keyword: '' })
    fetchFirstPage()
  }
})

function fetchFirstPage() {
  bankStore.fetchQuestions({ page: 1, current: 1 })
}

function buildFilters() {
  return {
    province: selectedProvince.value || '',
    dimension: selectedDimension.value || '',
    examCategory: examCategoryFilter.value || '',
    subcategory: subcategoryFilter.value || '',
    subcategory2: subcategory2Filter.value || '',
    year: (yearFilter.value || []).join(','),
    categoryReview: categoryReviewFilter.value || '',
    position: showPositionFilter.value ? selectedPosition.value || '' : '',
    keyword: keyword.value.trim()
  }
}

function onProvinceChange(event) {
  const selected = provinceOptions.value[Number(event.detail.value)]
  selectedProvince.value = selected?.code || 'national'
  if (selectedProvince.value !== 'jiangsu') selectedPosition.value = ''
  if (!hasToken()) return
  onFilterChange()
}

function onExamCategoryChange(event) {
  const selected = examCategoryOptions.value[Number(event.detail.value)]
  examCategoryFilter.value = selected?.code || ''
  subcategoryFilter.value = ''
  subcategory2Filter.value = ''
  if (!hasToken()) return
  onFilterChange()
}

function onCategoryChange(event) {
  const selected = QUESTION_CATEGORIES[Number(event.detail.value)]
  selectedDimension.value = selected?.key || ''
  if (!hasToken()) return
  onFilterChange()
}

function onDimensionChange(event) {
  const selected = dimensionOptions.value[Number(event.detail.value)]
  selectedDimension.value = selected?.key || ''
  if (!hasToken()) return
  onFilterChange()
}

function onPositionChange(event) {
  const selected = positionOptions.value[Number(event.detail.value)]
  selectedPosition.value = selected?.code || ''
  if (!hasToken()) return
  onFilterChange()
}

function onCategoryReviewChange(event) {
  const selected = categoryReviewOptions.value[Number(event.detail.value)]
  categoryReviewFilter.value = selected?.value || ''
  if (!hasToken()) return
  onFilterChange()
}

function onYearChange(event) {
  yearFilter.value = event.detail.value || []
}

function onFilterChange() {
  if (!promptLoginForAction('检索题库', '/pages/bank/index')) return
  if (readonlyMode.value) return
  bankStore.setFilters(buildFilters())
  fetchFirstPage()
}

function goPage(page) {
  if (!promptLoginForAction('浏览题库列表', '/pages/bank/index')) return
  if (readonlyMode.value) return
  bankStore.fetchQuestions({ current: page, pageSize: bankStore.pagination.pageSize })
}

function openDetail(question) {
  if (!promptLoginForAction('查看题目详情', `/pages/bank/detail?id=${encodeURIComponent(question.id)}`)) return
  if (readonlyMode.value) return
  uni.navigateTo({ url: `/pages/bank/detail?id=${encodeURIComponent(question.id)}` })
}

async function onDelete(question) {
  if (readonlyMode.value) return
  showLoading('删除中')
  try {
    await bankStore.removeQuestion(question.id)
    toast('删除成功', 'success')
  } catch (e) {
    toast(e?.message || '删除失败')
  } finally {
    hideLoading()
  }
}

function goEdit(question) {
  if (!promptLoginForAction('编辑题目', `/pages/admin/question-edit?id=${encodeURIComponent(question.id)}`)) return
  uni.navigateTo({ url: `/pages/admin/question-edit?id=${encodeURIComponent(question.id)}` })
}

function goAdd() {
  if (!promptLoginForAction('新增题目', '/pages/admin/question-edit')) return
  uni.navigateTo({ url: '/pages/admin/question-edit' })
}

function goImport() {
  if (!promptLoginForAction('导入题库', '/pages/admin/import')) return
  uni.navigateTo({ url: '/pages/admin/import' })
}

function goPricing() {
  if (!promptLoginForAction('开通套餐', '/pages/pricing/index')) return
  uni.navigateTo({ url: '/pages/pricing/index' })
}

function startTrial() {
  if (!promptLoginForAction('试用 1 题', '/pages/exam/prepare?trial=1')) return
  uni.navigateTo({ url: '/pages/exam/prepare?trial=1' })
}

async function startRandomPractice() {
  if (!promptLoginForAction('随机练习', '/pages/bank/index')) return
  if (readonlyMode.value) return
  try {
    const questions = await bankStore.fetchRandom({ count: 1, province: selectedProvince.value || '' })
    if (questions && questions.length) {
      uni.navigateTo({ url: `/pages/exam/prepare?random=1&qid=${encodeURIComponent(questions[0].id)}` })
    } else {
      toast('暂无可用题目')
    }
  } catch (e) {
    toast('获取随机题目失败')
  }
}

function onDocxProvinceChange(event) {
  docxProvince.value = DOCX_PROVINCES[Number(event.detail.value)]?.code || 'national'
}

function chooseDocxFile() {
  uni.chooseMessageFile({
    count: 1,
    type: 'file',
    extension: ['.docx', '.doc'],
    success(res) {
      const file = res.tempFiles[0]
      docxFileName.value = file.name
      docxFilePath.value = file.path
      docxResult.value = null
    },
    fail(e) {
      if (e.errMsg !== 'chooseMessageFile:fail cancel') {
        toast('选择文件失败')
      }
    }
  })
}

async function handleDocxImport() {
  if (!docxFilePath.value) {
    toast('请先选择要上传的 docx 文件')
    return
  }
  docxImporting.value = true
  docxResult.value = null
  try {
    const res = await importDocx(docxFilePath.value, docxProvince.value)
    const data = typeof res === 'string' ? JSON.parse(res) : res
    docxResult.value = data.data || data
    toast(`导入成功：${docxResult.value.imported} 题`, 'success')
    docxFileName.value = ''
    docxFilePath.value = ''
    onFilterChange()
  } catch (e) {
    toast(e?.message || '导入失败')
  } finally {
    docxImporting.value = false
  }
}
</script>

<style scoped>
.bank-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  flex-wrap: wrap;
  gap: 12rpx;
}

.bank-header__actions {
  display: flex;
  gap: 10rpx;
}

.bank-header__actions .primary-button,
.bank-header__actions .secondary-button {
  padding: 12rpx 20rpx;
  font-size: 24rpx;
}

.filter-card {
  padding-bottom: 18rpx;
}

.access-card {
  border-color: #bfd7ef;
  background: #f4f9fe;
}

.access-card__desc {
  display: block;
  color: #5f6f83;
  font-size: 24rpx;
  line-height: 1.6;
}

.access-card__actions {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 16rpx;
  margin-top: 22rpx;
}

.filter-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 20rpx 0;
  border-bottom: 1rpx solid #eef2f6;
  color: #2a3648;
  font-size: 27rpx;
}

.filter-row--input {
  gap: 16rpx;
}

.filter-row__value {
  color: #1b5faa;
  font-weight: 600;
  text-align: right;
  max-width: 440rpx;
}

.filter-input {
  flex: 1;
  text-align: right;
  color: #1b5faa;
  font-size: 27rpx;
}

.search-row {
  display: grid;
  grid-template-columns: minmax(0, 1fr) 150rpx;
  gap: 14rpx;
  margin-top: 18rpx;
}

.search-row__button {
  min-height: 88rpx;
}

.load-more {
  margin-top: 12rpx;
}

.quick-actions {
  margin-top: 18rpx;
}

.quick-actions__btn {
  width: 100%;
}

.bank-item {
  margin-bottom: 16rpx;
}

.bank-item__header {
  display: flex;
  align-items: center;
  gap: 12rpx;
  margin-bottom: 8rpx;
}

.bank-item__points {
  color: #6f7c8f;
  font-size: 22rpx;
  margin-left: auto;
}

.review-tag {
  padding: 6rpx 14rpx;
  border-radius: 999rpx;
  font-size: 22rpx;
}

.review-tag--pending {
  background: rgba(250, 140, 22, 0.1);
  color: #d48806;
}

.review-tag--confirmed {
  background: rgba(82, 196, 26, 0.1);
  color: #389e0d;
}

.bank-item__stem {
  min-width: 0;
}

.bank-item__actions {
  display: flex;
  justify-content: flex-end;
  gap: 12rpx;
  margin-top: 12rpx;
}

.secondary-button--danger {
  color: #cf1322;
  border-color: #ffa39e;
}

.pagination {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 16rpx;
  margin-top: 24rpx;
  padding: 16rpx 0;
}

.pagination__btn {
  min-width: 140rpx;
}

.pagination__info {
  color: #6f7c8f;
  font-size: 26rpx;
}

.year-overlay {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: rgba(0, 0, 0, 0.4);
  z-index: 1000;
  display: flex;
  align-items: flex-end;
  justify-content: center;
}

.year-modal {
  width: 100%;
  max-height: 60vh;
  border-radius: 24rpx 24rpx 0 0;
  overflow-y: auto;
  padding-bottom: env(safe-area-inset-bottom);
}

.year-checkbox {
  display: flex;
  align-items: center;
  gap: 16rpx;
  padding: 22rpx 0;
  border-bottom: 1rpx solid #eef2f6;
  font-size: 27rpx;
  color: #2a3648;
}

.filter-row--year {
  cursor: pointer;
}

.docx-form {
  padding: 10rpx 0;
}

.docx-form__label {
  display: block;
  color: #2a3648;
  font-size: 27rpx;
  font-weight: 600;
  margin-bottom: 8rpx;
}

.docx-file-name {
  display: block;
  margin-top: 10rpx;
  padding: 10rpx 16rpx;
  border-radius: 8rpx;
  background: #eef6ff;
  color: #1b5faa;
  font-size: 24rpx;
}

.docx-result {
  margin-top: 20rpx;
  padding: 18rpx;
  border-radius: 12rpx;
  background: #f6ffed;
  border: 1rpx solid #b7eb8f;
  color: #389e0d;
  font-size: 26rpx;
  line-height: 1.6;
}
</style>
