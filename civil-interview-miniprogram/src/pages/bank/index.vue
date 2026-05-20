<template>
  <view class="page page--tab">
    <text class="page-title">题库</text>
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
        <picker v-if="showPositionFilter" :range="positionNames" :value="positionIndex" @change="onPositionChange">
          <view class="filter-row">
            <text>岗位系统</text>
            <text class="filter-row__value">{{ selectedPositionName }}</text>
          </view>
        </picker>
        <view class="search-row">
          <input v-model="keyword" class="field search-row__input" placeholder="搜索题干关键词" confirm-type="search" @confirm="applySearch" />
          <button class="secondary-button search-row__button" @tap="applySearch">搜索</button>
        </view>
      </view>

      <view v-if="bankStore.questions.length">
        <QuestionCard
          v-for="question in bankStore.questions"
          :key="question.id"
          :question="question"
          @select="openDetail"
        />
      </view>
      <view v-else class="card">
        <EmptyState title="暂无题目" desc="换个省份或题型再试试。" />
      </view>

      <button
        v-if="bankStore.pagination.total > bankStore.questions.length"
        class="secondary-button load-more"
        :loading="bankStore.loading"
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
import QuestionCard from '../../components/QuestionCard.vue'
import { useBillingStore } from '../../stores/billing'
import { useQuestionBankStore } from '../../stores/questionBank'
import { useSubscriptionStore } from '../../stores/subscription'
import { useUserStore } from '../../stores/user'
import { PROVINCES, QUESTION_CATEGORIES } from '../../utils/constants'
import { JIANGSU_TARGETED_POSITIONS } from '../../utils/jiangsuJobs'
import { requireLogin } from '../../utils/navigation'

const billingStore = useBillingStore()
const bankStore = useQuestionBankStore()
const subscriptionStore = useSubscriptionStore()
const userStore = useUserStore()
const keyword = ref(bankStore.filters.keyword || '')
const selectedProvince = ref(userStore.selectedProvince || 'national')
const selectedDimension = ref('')
const selectedPosition = ref('')
const provinceOptions = computed(() => userStore.provinces.length ? userStore.provinces : PROVINCES)
const provinceNames = computed(() => provinceOptions.value.map((item) => item.name))
const categoryNames = computed(() => QUESTION_CATEGORIES.map((item) => item.name))
const showPositionFilter = computed(() => selectedProvince.value === 'jiangsu')
const positionOptions = computed(() => [
  { code: '', name: '全部岗位系统' },
  ...JIANGSU_TARGETED_POSITIONS
])
const positionNames = computed(() => positionOptions.value.map((item) => item.name))
const provinceIndex = computed(() => Math.max(0, provinceOptions.value.findIndex((item) => item.code === selectedProvince.value)))
const categoryIndex = computed(() => Math.max(0, QUESTION_CATEGORIES.findIndex((item) => item.key === selectedDimension.value)))
const positionIndex = computed(() => Math.max(0, positionOptions.value.findIndex((item) => item.code === selectedPosition.value)))
const selectedProvinceName = computed(() => provinceOptions.value[provinceIndex.value]?.name || '国考')
const selectedCategoryName = computed(() => QUESTION_CATEGORIES[categoryIndex.value]?.name || '全部题型')
const selectedPositionName = computed(() => positionOptions.value[positionIndex.value]?.name || '全部岗位系统')
const hasFullAccess = computed(() => (
  userStore.isAdmin
  || billingStore.isPaid
  || subscriptionStore.hasPremiumAccess
  || userStore.userInfo?.billing?.isPaid === true
  || userStore.userInfo?.permissions?.canAccessPremiumModules === true
))
const readonlyMode = computed(() => !hasFullAccess.value)

onShow(async () => {
  if (!requireLogin()) return
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
    bankStore.setFilters({ province: '', dimension: '', position: '', keyword: '' })
    fetchFirstPage()
  }
})

function fetchFirstPage() {
  bankStore.fetchQuestions({ page: 1, current: 1 })
}

function onProvinceChange(event) {
  const selected = provinceOptions.value[Number(event.detail.value)]
  selectedProvince.value = selected?.code || 'national'
  if (selectedProvince.value !== 'jiangsu') selectedPosition.value = ''
}

function onCategoryChange(event) {
  const selected = QUESTION_CATEGORIES[Number(event.detail.value)]
  selectedDimension.value = selected?.key || ''
}

function onPositionChange(event) {
  const selected = positionOptions.value[Number(event.detail.value)]
  selectedPosition.value = selected?.code || ''
}

function applySearch() {
  if (readonlyMode.value) return
  bankStore.setFilters({
    province: selectedProvince.value || '',
    dimension: selectedDimension.value || '',
    position: showPositionFilter.value ? selectedPosition.value || '' : '',
    keyword: keyword.value.trim()
  })
  fetchFirstPage()
}

async function loadMore() {
  if (readonlyMode.value) return
  const nextPage = bankStore.pagination.current + 1
  await bankStore.fetchMore({ page: nextPage, current: nextPage })
}

function openDetail(question) {
  if (readonlyMode.value) return
  uni.navigateTo({ url: `/pages/bank/detail?id=${encodeURIComponent(question.id)}` })
}

function goPricing() {
  uni.navigateTo({ url: '/pages/pricing/index' })
}

function startTrial() {
  uni.navigateTo({ url: '/pages/exam/prepare?trial=1' })
}
</script>

<style scoped>
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
  padding: 20rpx 0;
  border-bottom: 1rpx solid #eef2f6;
  color: #2a3648;
  font-size: 27rpx;
}

.filter-row__value {
  color: #1b5faa;
  font-weight: 600;
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
</style>
