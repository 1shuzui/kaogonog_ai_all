<!--
这个小程序题库管理页让管理员查找题目并进入编辑，列表只做筛选和跳转。

@param: 无；页面运行时从 props、路由参数、Pinia 状态和用户点击中拿数据。
@return: 渲染当前业务界面，并把按钮、表单或跳转事件交给既有流程处理。
@raises: 不主动抛业务异常；接口失败、未登录和权限不足由请求层或页面提示承接。
-->
<template>
  <view class="page">
    <view class="page-head">
      <view>
        <text class="page-title">题库管理</text>
        <text class="page-desc">管理员可维护全部题目，包括标准题库。</text>
      </view>
      <button v-if="userStore.isAdmin" class="primary-button page-head__button" @tap="goCreate">新增</button>
    </view>

    <view v-if="!userStore.isAdmin" class="card">
      <EmptyState title="无管理员权限" desc="请使用管理员账号登录后再访问。" />
    </view>

    <template v-else>
      <view class="card filter-card">
        <picker :range="provinceNames" :value="provinceIndex" @change="onProvinceChange">
          <view class="filter-row">
            <text>省份</text>
            <text class="filter-row__value">{{ selectedProvinceName }}</text>
          </view>
        </picker>
        <picker :range="categoryNames" :value="categoryIndex" @change="onCategoryChange">
          <view class="filter-row">
            <text>题型</text>
            <text class="filter-row__value">{{ selectedCategoryName }}</text>
          </view>
        </picker>
        <picker :range="examCategoryNames" :value="examCategoryIndex" @change="onExamCategoryChange">
          <view class="filter-row">
            <text>考试大类</text>
            <text class="filter-row__value">{{ selectedExamCategoryName }}</text>
          </view>
        </picker>
        <view class="filter-row filter-row--input">
          <text>{{ subcategoryLabel }}</text>
          <input v-model="subcategoryFilter" class="filter-row__input-field" placeholder="输入筛选" />
        </view>
        <view class="filter-row filter-row--input">
          <text>四级分类</text>
          <input v-model="subcategory2Filter" class="filter-row__input-field" placeholder="输入筛选" />
        </view>
        <view class="filter-row filter-row--input">
          <text>年份</text>
          <input v-model="yearFilter" class="filter-row__input-field" placeholder="如：2024,2023" />
        </view>
        <view class="search-row">
          <input v-model="keyword" class="field search-row__input" placeholder="搜索题干关键词" confirm-type="search" @confirm="fetchFirstPage" />
          <button class="secondary-button search-row__button" :loading="loading" @tap="fetchFirstPage">搜索</button>
        </view>
      </view>

      <view v-if="questions.length">
        <view v-for="question in questions" :key="question.id" class="card question-item">
          <view class="question-item__head">
            <text class="question-item__id">{{ question.id }}</text>
            <text class="question-item__source">{{ question.questionSourceLabel || '手动题目' }}</text>
          </view>
          <text class="question-item__stem">{{ compactText(question.stem, 86) }}</text>
          <view class="question-item__meta">
            <text>{{ categoryName(question.dimension) }}</text>
            <text>{{ provinceName(question.province) }}</text>
            <text v-if="question.examCategory">{{ question.examCategory }}</text>
            <text v-if="question.subcategory">{{ question.subcategory }}</text>
            <text>{{ question.prepTime || 90 }} / {{ question.answerTime || 180 }} 秒</text>
          </view>
          <view class="action-row">
            <button class="secondary-button" @tap="goEdit(question.id)">编辑</button>
            <button class="secondary-button danger-button" @tap="removeQuestion(question)">删除</button>
          </view>
        </view>
      </view>
      <view v-else class="card">
        <EmptyState title="暂无题目" desc="可以新增手动题目或调整筛选条件。" />
      </view>

      <button
        v-if="pagination.total > questions.length"
        class="secondary-button load-more"
        :loading="loading"
        @tap="loadMore"
      >
        加载更多
      </button>
    </template>
  </view>
</template>

<script setup>
import { computed, ref } from 'vue'
import { onShow } from '@dcloudio/uni-app'
import EmptyState from '../../components/EmptyState.vue'
import { deleteQuestion, getQuestions } from '../../api/questionBank'
import { useUserStore } from '../../stores/user'
import { PROVINCES, QUESTION_CATEGORIES, EXAM_CATEGORIES, SUBCATEGORY_LABELS, getCategoryName, getProvinceName } from '../../utils/constants'
import { compactText, normalizeListResponse } from '../../utils/format'
import { requireLogin, toast } from '../../utils/navigation'

const userStore = useUserStore()
const questions = ref([])
const loading = ref(false)
const keyword = ref('')
const selectedProvince = ref('')
const selectedDimension = ref('')
const selectedExamCategory = ref('')
const subcategoryFilter = ref('')
const subcategory2Filter = ref('')
const yearFilter = ref('')
const pagination = ref({
  current: 1,
  pageSize: 10,
  total: 0
})
const provinceOptions = computed(() => [{ code: '', name: '全部省份' }, ...(userStore.provinces.length ? userStore.provinces : PROVINCES)])
const provinceNames = computed(() => provinceOptions.value.map((item) => item.name))
const categoryNames = computed(() => QUESTION_CATEGORIES.map((item) => item.name))
const examCategoryNames = computed(() => EXAM_CATEGORIES.map((item) => item.name))
const provinceIndex = computed(() => Math.max(0, provinceOptions.value.findIndex((item) => item.code === selectedProvince.value)))
const categoryIndex = computed(() => Math.max(0, QUESTION_CATEGORIES.findIndex((item) => item.key === selectedDimension.value)))
const examCategoryIndex = computed(() => Math.max(0, EXAM_CATEGORIES.findIndex((item) => item.code === selectedExamCategory.value)))
const selectedProvinceName = computed(() => provinceOptions.value[provinceIndex.value]?.name || '全部省份')
const selectedCategoryName = computed(() => QUESTION_CATEGORIES[categoryIndex.value]?.name || '全部题型')
const selectedExamCategoryName = computed(() => EXAM_CATEGORIES[examCategoryIndex.value]?.name || '全部考试')
const subcategoryLabel = computed(() => {
  if (!selectedExamCategory.value) return '三级分类'
  return SUBCATEGORY_LABELS[selectedExamCategory.value] || '三级分类'
})

onShow(async () => {
  if (!requireLogin()) return
  await userStore.loadUserInfo().catch(() => null)
  await userStore.loadProvinces().catch(() => null)
  if (userStore.isAdmin) fetchFirstPage()
})

function provinceName(code) {
  return getProvinceName(code)
}

function categoryName(key) {
  return getCategoryName(key)
}

function onProvinceChange(event) {
  const selected = provinceOptions.value[Number(event.detail.value)]
  selectedProvince.value = selected?.code || ''
}

function onCategoryChange(event) {
  const selected = QUESTION_CATEGORIES[Number(event.detail.value)]
  selectedDimension.value = selected?.key || ''
}

function onExamCategoryChange(event) {
  const selected = EXAM_CATEGORIES[Number(event.detail.value)]
  selectedExamCategory.value = selected?.code || ''
  subcategoryFilter.value = ''
}

async function fetchPage(page = 1, append = false) {
  loading.value = true
  try {
    const response = await getQuestions({
      current: page,
      pageSize: pagination.value.pageSize,
      keyword: keyword.value.trim(),
      province: selectedProvince.value || '',
      dimension: selectedDimension.value || '',
      examCategory: selectedExamCategory.value || '',
      subcategory: subcategoryFilter.value.trim(),
      subcategory2: subcategory2Filter.value.trim(),
      year: yearFilter.value.trim()
    })
    const normalized = normalizeListResponse(response)
    questions.value = append ? [...questions.value, ...normalized.list] : normalized.list
    pagination.value = {
      ...pagination.value,
      current: page,
      total: normalized.total
    }
  } catch (error) {
    toast(error?.message || '题库加载失败')
  } finally {
    loading.value = false
  }
}

function fetchFirstPage() {
  fetchPage(1)
}

function loadMore() {
  fetchPage(pagination.value.current + 1, true)
}

function goCreate() {
  if (!userStore.isAdmin) return
  uni.navigateTo({ url: '/pages/admin/question-edit' })
}

function goEdit(id) {
  uni.navigateTo({ url: `/pages/admin/question-edit?id=${encodeURIComponent(id)}` })
}

function confirmDelete() {
  return new Promise((resolve) => {
    uni.showModal({
      title: '删除题目',
      content: '确认删除这道题吗？',
      confirmText: '删除',
      confirmColor: '#cf1322',
      success(res) {
        resolve(res.confirm)
      },
      fail() {
        resolve(false)
      }
    })
  })
}

async function removeQuestion(question) {
  if (!question?.id || !(await confirmDelete())) return
  try {
    await deleteQuestion(question.id)
    questions.value = questions.value.filter((item) => item.id !== question.id)
    pagination.value.total = Math.max(0, pagination.value.total - 1)
    toast('已删除', 'success')
  } catch (error) {
    toast(error?.message || '删除失败')
  }
}
</script>

<style scoped>
.page-head {
  display: grid;
  grid-template-columns: minmax(0, 1fr) 140rpx;
  gap: 18rpx;
  align-items: start;
}

.page-head__button {
  min-height: 76rpx;
}

.filter-card {
  padding-bottom: 18rpx;
}

.filter-row {
  display: flex;
  justify-content: space-between;
  padding: 20rpx 0;
  border-bottom: 1rpx solid #eef2f6;
  color: #2a3648;
  font-size: 27rpx;
}

.filter-row--input {
  align-items: center;
  gap: 16rpx;
}

.filter-row__value {
  color: #2F7FD6;
  font-weight: 600;
}

.filter-row__input-field {
  flex: 1;
  text-align: right;
  font-size: 26rpx;
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

.question-item {
  padding: 24rpx;
}

.question-item__head {
  display: flex;
  justify-content: space-between;
  gap: 16rpx;
}

.question-item__id,
.question-item__source,
.question-item__stem {
  display: block;
}

.question-item__id {
  color: #2F7FD6;
  font-size: 24rpx;
  font-weight: 800;
}

.question-item__source {
  color: #64748B;
  font-size: 22rpx;
}

.question-item__stem {
  margin-top: 12rpx;
  color: #172033;
  font-size: 28rpx;
  font-weight: 700;
  line-height: 1.55;
}

.question-item__meta {
  display: flex;
  flex-wrap: wrap;
  gap: 12rpx;
  margin-top: 14rpx;
  color: #64748B;
  font-size: 23rpx;
}

.action-row {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 14rpx;
  margin-top: 18rpx;
}

.load-more {
  margin-top: 12rpx;
}
</style>
