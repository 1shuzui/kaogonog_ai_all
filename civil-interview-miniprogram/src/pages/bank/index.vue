<!--
小程序题库页允许先浏览筛选结构，真实题目检索、题目详情和练习创建再按权益与登录态校验。
考试分类、地区、系统岗位和题型分类必须分开展示，避免把省份或题型误当成真实题源体系。

@param: 无；页面读取题库 store、用户权限和筛选控件状态。
@return: 渲染题库筛选、题目列表、管理员入口和未开通提示。
@raises: 不主动抛业务异常；接口失败、未登录和权限不足由请求层或页面提示承接。
-->
<template>
  <view class="motion-page page page--tab" :class="motionClass" :style="motionStyle">
    <view class="bank-header">
      <text class="page-title">{{ isAdmin ? '题库管理' : '题库' }}</text>
      <view v-if="!isAdmin" class="motion-heading-icon"><LearnerIcon name="read" :size="32" /></view>
      <view v-if="isAdmin" class="bank-header__actions">
        <button class="secondary-button" @tap="goImport">批量导入</button>
        <button class="secondary-button" @tap="showDocxModal = true">docx导入</button>
        <button class="primary-button" @tap="goAdd">新增题目</button>
      </view>
    </view>
    <text class="page-desc">选考试、地区和题型，找到真题后开始练习。</text>

    <view v-if="pageError" class="inline-status inline-status--error" role="alert">
      <text>{{ pageError }}</text>
      <button class="text-button" @tap="refreshPage">重新加载</button>
    </view>

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
        <LightSelector title="考试类型" :options="examCategoryOptions" :value="examCategoryIndex" @change="onExamCategoryChange">
          <button class="filter-row" :aria-label="'考试类型：' + selectedExamCategoryName">
            <text>考试类型</text>
            <text class="filter-row__value">{{ selectedExamCategoryName }}</text>
          </button>
        </LightSelector>
        <LightSelector title="地区（全国题源不含各省）" :options="provinceOptions" :value="provinceIndex" @change="onProvinceChange">
          <button class="filter-row" :aria-label="'地区：' + selectedProvinceName">
            <text>地区</text>
            <text class="filter-row__value">{{ selectedProvinceName }}</text>
          </button>
        </LightSelector>
        <LightSelector title="题型" :options="dimensionOptions" :value="dimensionIndex" @change="onDimensionChange">
          <button class="filter-row" :aria-label="'题型：' + selectedDimensionName">
            <text>题型</text>
            <text class="filter-row__value">{{ selectedDimensionName }}</text>
          </button>
        </LightSelector>
        <view class="search-row">
          <input v-model="keyword" class="field search-row__input" aria-label="搜索题干关键词" placeholder="搜索题干关键词" placeholder-class="search-placeholder" confirm-type="search" @confirm="onFilterChange" />
          <button class="secondary-button search-row__button" @tap="onFilterChange">搜索</button>
        </view>
        <text v-if="keyword.trim() !== (bankStore.filters.keyword || '')" class="filter-help">关键词尚未应用，点击搜索更新题目。</text>
        <MotionCollapse title="更多筛选" :open="showAdvancedFilters" :revision="[filtersLoading, filtersError, filterOptions, subcategoryFilter, subcategory2Filter, selectedProvince, examCategoryFilter]" @toggle="showAdvancedFilters = !showAdvancedFilters">
          <view v-if="readonlyMode" class="filter-help">开通题库后可查看实际分类和年份选项。</view>
          <view v-else-if="filtersLoading" class="filter-help" role="status">正在加载可用筛选项…</view>
          <view v-else-if="filtersError" class="inline-status inline-status--error" role="alert">
            <text>{{ filtersError }}，已选条件保留。</text>
            <button class="text-button" @tap="retryFilterOptions">重试选项</button>
          </view>
          <LightSelector v-if="showPositionFilter" title="岗位系统" :options="positionOptions" :value="positionIndex" @change="onPositionChange">
            <button class="filter-row" :aria-label="'岗位系统：' + selectedPositionName">
              <text>岗位系统</text>
              <text class="filter-row__value">{{ selectedPositionName }}</text>
            </button>
          </LightSelector>
          <LightSelector :title="subcategoryLabel" :options="subcategoryOptions" :value="subcategoryIndex" :disabled="!metadataReady || !filterOptions.subcategory.length || unavailableSubcategory" @change="onSubcategoryChange">
            <button class="filter-row" :disabled="!metadataReady || !filterOptions.subcategory.length || unavailableSubcategory" :aria-label="subcategoryLabel + '：' + (subcategoryFilter || '不限')">
              <text>{{ subcategoryLabel }}</text>
              <text class="filter-row__value">{{ subcategoryFilter || (metadataReady && !filterOptions.subcategory.length ? '暂无可选' : '不限') }}</text>
            </button>
          </LightSelector>
          <view v-if="subcategoryFilter" class="filter-help filter-help--action">
            <text>{{ unavailableSubcategory ? '已选值在当前条件下不可用，清除后可重新选择。' : '已保留分类条件。' }}</text>
            <button class="text-button" @tap="subcategoryFilter = ''; onFilterChange()">清除</button>
          </view>
          <LightSelector title="细分方向" :options="subcategory2Options" :value="subcategory2Index" :disabled="!metadataReady || !filterOptions.subcategory2.length || unavailableSubcategory2" @change="onSubcategory2Change">
            <button class="filter-row" :disabled="!metadataReady || !filterOptions.subcategory2.length || unavailableSubcategory2" :aria-label="'细分方向：' + (subcategory2Filter || '不限')">
              <text>细分方向</text>
              <text class="filter-row__value">{{ subcategory2Filter || (metadataReady && !filterOptions.subcategory2.length ? '暂无可选' : '不限') }}</text>
            </button>
          </LightSelector>
          <view v-if="subcategory2Filter" class="filter-help filter-help--action">
            <text>{{ unavailableSubcategory2 ? '已选值在当前条件下不可用，清除后可重新选择。' : '已保留细分方向。' }}</text>
            <button class="text-button" @tap="subcategory2Filter = ''; onFilterChange()">清除</button>
          </view>
          <button class="filter-row" :disabled="readonlyMode" :aria-label="'年份：' + yearLabel" @tap="openYearPicker">
            <text>年份</text>
            <text class="filter-row__value">{{ yearLabel }}</text>
          </button>
          <text v-if="metadataReady && !filterOptions.year.length" class="filter-help">{{ questionCount ? '当前题目没有可筛选年份，选择不限年份可包含它们。' : '当前条件下暂无可用年份，可放宽筛选。' }}</text>
          <LightSelector v-if="isAdmin" title="分类复核" :options="categoryReviewOptions" :value="categoryReviewIndex" @change="onCategoryReviewChange">
            <button class="filter-row">
              <text>分类复核</text>
              <text class="filter-row__value">{{ selectedCategoryReviewName }}</text>
            </button>
          </LightSelector>
        </MotionCollapse>
        <view class="filter-summary">
          <text class="filter-summary__text">{{ filterSummary }}</text>
          <button class="text-button" @tap="resetFilters">重置</button>
        </view>
        <text v-if="filtersError && !showAdvancedFilters" class="filter-help">筛选选项加载失败，展开“更多筛选”可重试。</text>
    </view>

    <template v-if="!readonlyMode">
      <view class="results-head">
        <text class="results-head__count">{{ bankStore.loading || pageLoading ? '正在加载题目…' : bankStore.error ? '题目未能更新' : `共 ${bankStore.pagination.total} 道题` }}</text>
        <button class="text-button" @tap="startRandomPractice">随机练习</button>
      </view>
      <view v-if="bankStore.error" class="inline-status inline-status--error" role="alert">
        <text>{{ bankStore.error }}</text>
        <button class="text-button" @tap="retryQuestions">重试题目</button>
      </view>
      <text v-if="bankStore.questions.length && (bankStore.loading || bankStore.error || pageLoading)" class="filter-help">以下保留上次成功加载的题目，更新成功后替换。</text>
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
      <view v-else-if="!bankStore.loading && !bankStore.error && !pageLoading" class="card">
        <EmptyState title="当前筛选暂无题目" desc="可调整地区、题型，或重置全部筛选。" />
        <button class="secondary-button" @tap="resetFilters">重置筛选</button>
      </view>

      <view v-if="totalPages > 1 && !bankStore.error" class="pagination">
        <button class="secondary-button pagination__btn" :disabled="bankStore.loading || pageLoading || bankStore.pagination.current <= 1" @tap="goPage(bankStore.pagination.current - 1)">上一页</button>
        <text class="pagination__info">{{ bankStore.pagination.current }} / {{ totalPages }}</text>
        <button class="secondary-button pagination__btn" :disabled="bankStore.loading || pageLoading || bankStore.pagination.current >= totalPages" @tap="goPage(bankStore.pagination.current + 1)">下一页</button>
      </view>
    </template>

    <LearnerSheet class="bank-year-sheet" :show="showYearPicker" title="选择年份" close-label="完成" :body-height="yearOptions.length * 56 + unavailableYears.length * 56 + 240" @close="applyYearDraft">
        <text class="filter-help">可多选。点击完成或空白处关闭后应用；清空即不限年份。</text>
        <button class="text-button year-clear" @tap="yearDraft = []">不限年份（清空已选）</button>
        <text v-if="filtersLoading" class="filter-help" role="status">正在加载可用年份…</text>
        <view v-else-if="filtersError" class="inline-status inline-status--error" role="alert">
          <text>{{ filtersError }}，已选年份保留。</text>
          <button class="text-button" @tap="retryFilterOptions">重试选项</button>
        </view>
        <text v-else-if="!yearOptions.length" class="filter-help">{{ questionCount ? '当前题目没有可筛选年份，选择不限年份可包含它们。' : '当前条件下暂无可用年份。' }}</text>
        <view v-for="year in unavailableYears" :key="year" class="filter-help filter-help--action">
          <text>{{ year }}：已选，当前不可用</text>
          <button class="text-button" :aria-label="'移除已选年份' + year" @tap="yearDraft = yearDraft.filter(value => value !== year)">移除</button>
        </view>
        <checkbox-group v-if="metadataReady" @change="onYearChange">
          <label v-for="opt in yearOptions" :key="opt.value" class="year-checkbox">
            <checkbox :value="opt.value" :checked="opt.checked" />
            <text>{{ opt.value }} 年</text>
          </label>
        </checkbox-group>
    </LearnerSheet>

    <LearnerSheet :show="showDocxModal && isAdmin" title="docx 题库导入" close-label="取消" :body-height="440" @close="showDocxModal = false">
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
    </LearnerSheet>
  </view>
</template>

<script setup>
import { miniPracticeUrl } from '../../../../shared/practiceSelection.mjs'
import LearnerIcon from '../../components/LearnerIcon.vue'
import { usePageMotion } from '../../motion/useMotion'
const { motionClass, motionStyle } = usePageMotion()
import { computed, ref, watch } from 'vue'
import { onShow } from '@dcloudio/uni-app'
import EmptyState from '../../components/EmptyState.vue'
import QuestionCard from '../../components/QuestionCard.vue'
import LearnerSheet from '../../components/LearnerSheet.vue'
import LightSelector from '../../components/LightSelector.vue'
import MotionCollapse from '../../components/MotionCollapse.vue'
import { importDocx } from '../../api/questionBank'
import { useBillingStore } from '../../stores/billing'
import { useQuestionBankStore } from '../../stores/questionBank'
import { useSubscriptionStore } from '../../stores/subscription'
import { useUserStore } from '../../stores/user'
import { hasPremiumAccess } from '../../utils/access'
import { EXAM_CATEGORIES, PROVINCES, QUESTION_CATEGORIES, SUBCATEGORY_LABELS } from '../../utils/constants'
import { useQuestionFilters } from '../../utils/useQuestionFilters'
import { JIANGSU_TARGETED_POSITIONS } from '../../utils/jiangsuJobs'
import { hideLoading, hasToken, promptLoginForAction, showLoading, toast } from '../../utils/navigation'

const billingStore = useBillingStore()
const bankStore = useQuestionBankStore()
const subscriptionStore = useSubscriptionStore()
const userStore = useUserStore()
const isAdmin = computed(() => userStore.isAdmin)
const keyword = ref(bankStore.filters.keyword || '')
const selectedProvince = ref(bankStore.filtersInitialized ? bankStore.filters.province : userStore.selectedProvince || 'national')
const examCategoryFilter = ref(bankStore.filters.examCategory || '')
const selectedDimension = ref(bankStore.filters.dimension || '')
const subcategoryFilter = ref(bankStore.filters.subcategory || '')
const subcategory2Filter = ref(bankStore.filters.subcategory2 || '')
const yearFilter = ref(String(bankStore.filters.year || '').split(',').filter(Boolean))
const categoryReviewFilter = ref(bankStore.filters.categoryReview || '')
const selectedPosition = ref(bankStore.filters.position || '')
const showYearPicker = ref(false)
const yearDraft = ref([])
const showAdvancedFilters = ref(false)
const pageLoading = ref(false)
const pageError = ref('')
const requestedPage = ref(1)
let showRequest = 0
let filterRevision = 0
const { options: filterOptions, loading: filtersLoading, error: filtersError, questionCount, refresh: refreshFilterOptions } = useQuestionFilters()
const showDocxModal = ref(false)
const docxImporting = ref(false)
const docxFileName = ref('')
const docxFilePath = ref('')
const docxProvince = ref('national')
const docxResult = ref(null)

const provinceOptions = computed(() => [
  { code: '', name: '全部地区' },
  ...(userStore.provinces.length ? userStore.provinces : PROVINCES)
    .filter((item) => item.code && item.code !== 'all')
    .map((item) => ({ ...item, name: item.code === 'national' ? '全国题源' : item.name }))
])
const provinceIndex = computed(() => Math.max(0, provinceOptions.value.findIndex((item) => item.code === selectedProvince.value)))
const selectedProvinceName = computed(() => provinceOptions.value.find((item) => item.code === selectedProvince.value)?.name || selectedProvince.value || '全部地区')

const examCategoryOptions = computed(() => [{ code: '', name: '全部考试类型' }, ...EXAM_CATEGORIES.filter((item) => item.code)])
const examCategoryIndex = computed(() => Math.max(0, examCategoryOptions.value.findIndex((item) => item.code === examCategoryFilter.value)))
const selectedExamCategoryName = computed(() => examCategoryOptions.value.find((item) => item.code === examCategoryFilter.value)?.name || examCategoryFilter.value || '全部考试类型')

const subcategoryLabel = computed(() => SUBCATEGORY_LABELS[examCategoryFilter.value] || '分类方向')
const subcategoryOptions = computed(() => [{ value: '', label: `不限${subcategoryLabel.value}` }, ...filterOptions.value.subcategory.map(value => ({ value, label: value }))])
const subcategory2Options = computed(() => [{ value: '', label: '不限细分方向' }, ...filterOptions.value.subcategory2.map(value => ({ value, label: value }))])
const subcategoryIndex = computed(() => subcategoryOptions.value.findIndex(item => item.value === subcategoryFilter.value))
const subcategory2Index = computed(() => subcategory2Options.value.findIndex(item => item.value === subcategory2Filter.value))
const metadataReady = computed(() => !readonlyMode.value && !filtersLoading.value && !filtersError.value)
const unavailableSubcategory = computed(() => metadataReady.value && !!subcategoryFilter.value && subcategoryIndex.value < 0)
const unavailableSubcategory2 = computed(() => metadataReady.value && !!subcategory2Filter.value && subcategory2Index.value < 0)

const dimensionOptions = computed(() => [{ key: '', name: '全部题型' }, ...QUESTION_CATEGORIES.filter((item) => item.key)])
const dimensionIndex = computed(() => Math.max(0, dimensionOptions.value.findIndex((item) => item.key === selectedDimension.value)))
const selectedDimensionName = computed(() => dimensionOptions.value.find((item) => item.key === selectedDimension.value)?.name || selectedDimension.value || '全部题型')

const categoryReviewOptions = computed(() => [
  { value: '', label: '全部复核状态' },
  { value: 'needs_review', label: '分类待确认' },
  { value: 'confirmed', label: '分类已确认' }
])
const categoryReviewIndex = computed(() => Math.max(0, categoryReviewOptions.value.findIndex((item) => item.value === categoryReviewFilter.value)))
const selectedCategoryReviewName = computed(() => categoryReviewOptions.value[categoryReviewIndex.value]?.label || '全部复核状态')

const showPositionFilter = computed(() => selectedProvince.value === 'jiangsu')
const positionOptions = computed(() => [
  { code: '', name: '全部岗位系统' },
  ...JIANGSU_TARGETED_POSITIONS
])
const positionIndex = computed(() => Math.max(0, positionOptions.value.findIndex((item) => item.code === selectedPosition.value)))
const selectedPositionName = computed(() => positionOptions.value[positionIndex.value]?.name || '全部岗位系统')

const yearOptions = computed(() => filterOptions.value.year.map(value => ({ value, checked: yearDraft.value.includes(value) })))
const unavailableYears = computed(() => metadataReady.value ? yearDraft.value.filter(value => !filterOptions.value.year.includes(value)) : [])
const yearLabel = computed(() => yearFilter.value.length ? yearFilter.value.join('、') : '不限年份（可多选）')
const filterSummary = computed(() => [
  selectedExamCategoryName.value, selectedProvinceName.value, selectedDimensionName.value,
  showPositionFilter.value && selectedPosition.value ? selectedPositionName.value : '',
  subcategoryFilter.value, subcategory2Filter.value, yearFilter.value.join('、'),
  bankStore.filters.keyword ? `关键词：${bankStore.filters.keyword}` : '',
  isAdmin.value && categoryReviewFilter.value ? selectedCategoryReviewName.value : ''
].filter(Boolean).join(' · '))

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

onShow(refreshPage)

watch(() => [userStore.token, hasFullAccess.value], ([token, access], [oldToken]) => {
  if (token === oldToken && token && access) return
  // Cancel metadata before clearing account-scoped content, even on a cached tab.
  refreshFilterOptions({}, false)
  showRequest += 1
  bankStore.$reset()
  pageLoading.value = false
  pageError.value = ''
  showYearPicker.value = false
  showDocxModal.value = false
  if (token !== oldToken) resetFilterValues(userStore.selectedProvince || 'national')
}, { flush: 'sync' })

async function refreshPage() {
  const request = ++showRequest
  const account = userStore.token
  pageError.value = ''
  if (!hasToken()) {
    await refreshFilterOptions({}, false)
    bankStore.$reset()
    return
  }
  pageLoading.value = true
  try {
    const results = await Promise.allSettled([
      userStore.loadProvinces(),
      userStore.loadUserInfo(),
      subscriptionStore.refresh({ skipErrorHandler: true })
    ])
    if (request !== showRequest || account !== userStore.token || !hasToken()) return
    if (results.some(result => result.status === 'rejected')) pageError.value = '账号或地区信息未能完整刷新，请重试。'
    if (!bankStore.filtersInitialized && filterRevision === 0) selectedProvince.value = userStore.selectedProvince || 'national'
    if (readonlyMode.value) {
      await refreshFilterOptions({}, false)
      bankStore.$reset()
      return
    }
    const snapshot = buildFilters()
    bankStore.setFilters(snapshot)
    // Initialization is done. The store/hook own request loading, including supersession.
    pageLoading.value = false
    await Promise.all([refreshFilterOptions(metadataParams(snapshot), true), fetchFirstPage()])
  } catch (cause) {
    if (request === showRequest) pageError.value = cause?.message || '题库暂时无法加载，请重试。'
  } finally {
    if (request === showRequest) pageLoading.value = false
  }
}

async function fetchFirstPage() {
  requestedPage.value = 1
  try { await bankStore.fetchQuestions({ page: 1, current: 1 }) } catch { /* store owns the current inline error */ }
}

function metadataParams(snapshot) {
  const { year, categoryReview, ...params } = snapshot
  return { ...params, year: '' }
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
  selectedProvince.value = selected?.code || ''
  if (selectedProvince.value !== 'jiangsu') selectedPosition.value = ''
  if (!hasToken()) return
  onFilterChange()
}

function onExamCategoryChange(event) {
  const selected = examCategoryOptions.value[Number(event.detail.value)]
  examCategoryFilter.value = selected?.code || ''
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
  // Unavailable retained years are not checkboxes; only an explicit clear removes them.
  yearDraft.value = [...new Set([
    ...yearDraft.value.filter(value => !filterOptions.value.year.includes(value)),
    ...(event.detail.value || []).filter(value => filterOptions.value.year.includes(value))
  ])]
}

function openYearPicker() {
  if (readonlyMode.value) return
  yearDraft.value = [...yearFilter.value]
  showYearPicker.value = true
}

async function applyYearDraft() {
  if (!showYearPicker.value) return
  showYearPicker.value = false
  if (yearDraft.value.length === yearFilter.value.length && yearDraft.value.every(value => yearFilter.value.includes(value))) return
  yearFilter.value = [...yearDraft.value]
  await onFilterChange()
}

function onSubcategoryChange(event) {
  subcategoryFilter.value = subcategoryOptions.value[Number(event.detail.value)]?.value || ''
  return onFilterChange()
}

function onSubcategory2Change(event) {
  subcategory2Filter.value = subcategory2Options.value[Number(event.detail.value)]?.value || ''
  return onFilterChange()
}

function resetFilterValues(province = '') {
  selectedProvince.value = province
  selectedDimension.value = ''
  examCategoryFilter.value = ''
  subcategoryFilter.value = ''
  subcategory2Filter.value = ''
  yearFilter.value = []
  yearDraft.value = []
  selectedPosition.value = ''
  categoryReviewFilter.value = ''
  keyword.value = ''
}

function resetFilters() {
  resetFilterValues()
  return onFilterChange()
}

function retryFilterOptions() {
  const snapshot = { ...buildFilters(), keyword: bankStore.filters.keyword || '' }
  return refreshFilterOptions(metadataParams(snapshot), hasToken() && !readonlyMode.value)
}

async function onFilterChange() {
  filterRevision += 1
  if (!promptLoginForAction('检索题库', '/pages/bank/index')) return
  const snapshot = buildFilters()
  bankStore.setFilters(snapshot)
  await Promise.all([
    refreshFilterOptions(metadataParams(snapshot), !readonlyMode.value),
    readonlyMode.value ? Promise.resolve() : fetchFirstPage()
  ])
}

async function goPage(page) {
  if (!promptLoginForAction('浏览题库列表', '/pages/bank/index')) return
  if (readonlyMode.value) return
  requestedPage.value = page
  try { await bankStore.fetchQuestions({ current: page, pageSize: bankStore.pagination.pageSize }) } catch { /* keep the last usable list visible */ }
}

function retryQuestions() {
  return goPage(requestedPage.value)
}

function openDetail(question) {
  if (!promptLoginForAction('查看题目详情', `/pages/bank/detail?id=${encodeURIComponent(question.id)}`)) return
  if (readonlyMode.value) return
  uni.navigateTo({ url: `/pages/bank/detail?id=${encodeURIComponent(question.id)}&filterSnapshot=${encodeURIComponent(JSON.stringify(buildFilters()))}` })
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
    const filters = buildFilters()
    const questions = await bankStore.fetchRandom({ ...filters, count: 1 })
    if (questions && questions.length) {
      uni.navigateTo({ url: miniPracticeUrl({ source: 'bank', questionId: questions[0].id, filters }) })
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
.page { color: var(--ui-text); }
.page-desc { display: block; margin: 8px 0 16px; color: var(--ui-muted); font-size: 14px; line-height: 1.6; }
.bank-header { display: flex; align-items: center; justify-content: space-between; flex-wrap: wrap; gap: 12px; }
.bank-header__actions { display: flex; flex-wrap: wrap; gap: 8px; }
.primary-button,
.secondary-button { min-height: 44px; min-width: 44px; font-size: 14px; }
.bank-header__actions .primary-button,
.bank-header__actions .secondary-button { padding: 8px 12px; }

.filter-card { padding-top: 8px; padding-bottom: 8px; }
.filter-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
  width: 100%;
  min-height: 44px;
  margin: 0;
  padding: 10px 0;
  box-sizing: border-box;
  border-radius: 0;
  border-bottom: 1px solid var(--ui-border);
  background: transparent;
  color: var(--ui-text);
  font-size: 15px;
  line-height: 1.5;
  text-align: left;
}
.filter-row::after,
.text-button::after { border: 0; }
.filter-row > text:first-child { flex-shrink: 0; }
.filter-row__value { min-width: 0; max-width: 70%; color: var(--ui-link); text-align: right; font-weight: 600; overflow-wrap: anywhere; }
.filter-row[disabled],
.filter-row[disabled] .filter-row__value { color: var(--ui-muted); background: transparent; opacity: 1; }
.search-row { display: grid; grid-template-columns: minmax(0, 1fr) 72px; gap: 8px; margin-top: 12px; }
.search-row__input { min-width: 0; min-height: 44px; box-sizing: border-box; font-size: 15px; }
.search-placeholder { color: var(--ui-muted); font-size: 14px; }
.search-row__button { margin: 0; padding: 8px; }

.text-button {
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
  min-width: 44px;
  min-height: 44px;
  margin: 0;
  padding: 8px 12px;
  box-sizing: border-box;
  border-radius: 8px;
  background: transparent;
  color: var(--ui-link);
  font-size: 14px;
  line-height: 1.5;
}
.filter-row:focus-visible,
.text-button:focus-visible,
.secondary-button:focus-visible,
.primary-button:focus-visible { outline: 2px solid var(--ui-primary); outline-offset: 2px; }
.filter-help { display: block; margin: 8px 0; color: var(--ui-muted); font-size: 14px; line-height: 1.6; overflow-wrap: anywhere; }
.filter-help--action,
.filter-summary { display: flex; align-items: center; justify-content: space-between; gap: 8px; }
.filter-help--action > text,
.filter-summary__text { flex: 1; min-width: 0; }
.filter-summary { border-top: 1px solid var(--ui-border); margin-top: 8px; padding-top: 4px; }
.filter-summary__text { color: var(--ui-muted); font-size: 14px; line-height: 1.6; overflow-wrap: anywhere; }

.inline-status { display: flex; align-items: center; justify-content: space-between; gap: 8px; padding: 8px 12px; margin: 8px 0; border: 1px solid var(--ui-border); border-radius: 8px; background: var(--ui-surface); font-size: 14px; line-height: 1.6; }
.inline-status > text { flex: 1; min-width: 0; overflow-wrap: anywhere; }
.inline-status--error { color: var(--ui-error); }
.results-head { display: flex; align-items: center; justify-content: space-between; gap: 12px; margin-bottom: 8px; }
.results-head__count { color: var(--ui-muted); font-size: 14px; line-height: 1.6; }

.access-card { border-color: var(--ui-border); background: var(--ui-soft); }
.access-card__desc { display: block; color: var(--ui-muted); font-size: 14px; line-height: 1.6; }
.access-card__actions { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 12px; margin-top: 16px; }
.bank-item { margin-bottom: 16rpx; }
.bank-item__header { display: flex; align-items: center; flex-wrap: wrap; gap: 8px; margin-bottom: 8px; }
.bank-item__points { margin-left: auto; color: var(--ui-muted); font-size: 14px; line-height: 1.5; }
.review-tag { padding: 4px 8px; border-radius: 8px; font-size: 14px; line-height: 1.5; background: var(--ui-soft); }
.review-tag--pending { color: var(--ui-error); }
.review-tag--confirmed { color: var(--ui-success); }
.bank-item__stem { min-width: 0; }
.bank-item__actions { display: flex; justify-content: flex-end; flex-wrap: wrap; gap: 8px; margin-top: 12px; }
.secondary-button--danger { color: var(--ui-error); border-color: var(--ui-error); }
.pagination { display: flex; align-items: center; justify-content: center; gap: 12px; margin-top: 16px; padding: 12px 0; }
.pagination__btn { min-width: 72px; }
.pagination__info { color: var(--ui-muted); font-size: 14px; }

.year-clear { background: var(--ui-soft); margin: 8px 0; }
.year-checkbox { display: flex; align-items: center; gap: 12px; min-height: 44px; padding: 8px 0; box-sizing: border-box; border-bottom: 1px solid var(--ui-border); color: var(--ui-text); font-size: 15px; line-height: 1.6; }
.docx-form { padding: 8px 0; }
.docx-form__label { display: block; margin-bottom: 8px; color: var(--ui-text); font-size: 15px; line-height: 1.5; font-weight: 600; }
.docx-file-name { display: block; margin-top: 8px; padding: 8px 12px; border-radius: 8px; background: var(--ui-soft); color: var(--ui-link); font-size: 14px; line-height: 1.6; overflow-wrap: anywhere; }
.docx-result { margin-top: 16px; padding: 12px; border-radius: 8px; border: 1px solid var(--ui-border); color: var(--ui-success); font-size: 14px; line-height: 1.6; }
.docx-result text { display: block; }
</style>
