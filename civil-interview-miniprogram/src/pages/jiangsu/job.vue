<!--
江苏事业单位岗位页面向用户展示岗位方向，内部路由仍沿用历史 key，但可见文案不再出现 ABCDE 类。
筛选年份、地市和题型只用于江苏事业单位统考入口，不应把江苏省考 A/B/C 类或其他省份题源混进来。

@param: 无；页面从路由 key、江苏岗位常量和题库 store 组装筛选条件。
@return: 渲染岗位说明、地市/年份/题型筛选和对应题目列表。
@raises: 不主动抛业务异常；接口失败、未登录和权限不足由请求层或页面提示承接。
-->
<template>
  <view class="page">
    <view class="job-hero card">
      <text class="job-hero__eyebrow">2026 江苏事业单位统考</text>
      <text class="job-hero__title">{{ category.title }}</text>
      <text class="job-hero__desc">{{ categoryMeta }}</text>
      <text class="job-hero__tag">{{ category.hot }}</text>
    </view>

    <view class="filter-card card">
      <view class="filter-block">
        <text class="filter-block__label">地市</text>
        <scroll-view scroll-x class="filter-scroll">
          <view class="filter-scroll__inner">
            <view
              v-for="city in JIANGSU_CITY_FILTERS"
              :key="city.key"
              class="chip"
              :class="{ 'chip--active': filters.city === city.key }"
              @tap="filters.city = city.key"
            >
              {{ city.name }}
            </view>
          </view>
        </scroll-view>
      </view>

      <view class="filter-block">
        <text class="filter-block__label">年份</text>
        <view class="chip-row">
          <view class="chip" :class="{ 'chip--active': filters.year === '' }" @tap="filters.year = ''">全部</view>
          <view
            v-for="year in JIANGSU_YEAR_FILTERS"
            :key="year"
            class="chip"
            :class="{ 'chip--active': filters.year === year }"
            @tap="filters.year = year"
          >
            {{ year }}
          </view>
        </view>
      </view>

      <view class="filter-block">
        <text class="filter-block__label">题型</text>
        <view class="chip-row">
          <view class="chip" :class="{ 'chip--active': filters.type === '' }" @tap="filters.type = ''">全部</view>
          <view
            v-for="type in JIANGSU_QUESTION_TYPES"
            :key="type.key"
            class="chip"
            :class="{ 'chip--active': filters.type === type.key }"
            @tap="filters.type = type.key"
          >
            {{ type.name }}
          </view>
        </view>
      </view>
    </view>

    <view class="section-head">
      <text class="section-title">题目列表</text>
      <text class="muted">{{ listStatusText }}</text>
    </view>

    <view v-if="loading" class="card">
      <text class="loading-text">正在加载真实题库...</text>
    </view>
    <view v-else-if="filteredItems.length">
      <view v-for="item in filteredItems" :key="item.id" class="question-card card">
        <view class="question-card__meta">
          <text>{{ item.yearLabel }}</text>
          <text>{{ item.cityName }}</text>
          <text>{{ item.typeName }}</text>
        </view>
        <text class="question-card__title">{{ item.title }}</text>
        <text class="question-card__stem">{{ item.stem }}</text>
        <button class="primary-button question-card__button" @tap="goPractice(item)">开始刷题</button>
      </view>
    </view>
    <view v-else class="card">
      <EmptyState title="暂无匹配题目" :desc="emptyText" />
    </view>
  </view>
</template>

<script setup>
import { computed, reactive, ref } from 'vue'
import { onLoad } from '@dcloudio/uni-app'
import EmptyState from '../../components/EmptyState.vue'
import { getQuestions } from '../../api/questionBank'
import {
  JIANGSU_CITY_FILTERS,
  JIANGSU_QUESTION_TYPES,
  JIANGSU_YEAR_FILTERS,
  getJiangsuJobCategory
} from '../../utils/jiangsuJobs'
import { hasToken, promptLoginForAction } from '../../utils/navigation'

const categoryKey = ref('a')
const loading = ref(false)
const allItems = ref([])
const filters = reactive({
  city: 'all',
  year: '',
  type: ''
})

const category = computed(() => getJiangsuJobCategory(categoryKey.value))
const categoryMeta = computed(() => [category.value.scope, category.value.subtitle].filter(Boolean).join(' · '))
const positionCode = computed(() => `jiangsu_${category.value.key}`)
const listStatusText = computed(() => (loading.value ? '正在加载真实题库...' : `真实题库 · ${filteredItems.value.length} 题`))
const emptyText = computed(() => categoryKey.value === 'd'
  ? '当前江苏题库暂未收录教师岗真题，请先切换其他岗位或导入教师岗资料。'
  : '换个地市、年份或题型再试。')
const filteredItems = computed(() => allItems.value.filter((item) => {
  if (filters.city !== 'all' && item.cityKey !== filters.city) return false
  if (filters.year && item.year !== filters.year) return false
  if (filters.type && item.typeKey !== filters.type) return false
  return true
}))

onLoad((query) => {
  categoryKey.value = query?.category || 'a'
  if (!hasToken()) return
  loadQuestions()
})

function normalizeQuestion(item = {}) {
  const tags = Array.isArray(item.tags) ? item.tags : []
  const metaText = [item.sourceDocument, item.sourceFile, ...tags].join(' ')
  const year = String(metaText.match(/20\d{2}/)?.[0] || '')
  const city = JIANGSU_CITY_FILTERS.find((option) => option.key !== 'all' && metaText.includes(option.name))
  const type = JIANGSU_QUESTION_TYPES.find((option) => item.dimension === option.key || metaText.includes(option.name))
  return {
    ...item,
    year,
    yearLabel: year || '真题',
    cityKey: city?.key || 'all',
    cityName: city?.name || '江苏',
    typeKey: type?.key || item.dimension || '',
    typeName: type?.name || '结构化面试',
    title: `${year || '江苏'} · ${city?.name || '江苏'} · ${category.value.shortTitle} · ${type?.name || '结构化面试'}`
  }
}

async function loadQuestions() {
  loading.value = true
  try {
    const res = await getQuestions({
      province: 'jiangsu',
      examCategory: '事业单位考试',
      current: 1,
      page: 1,
      pageSize: 1000
    })
    allItems.value = (Array.isArray(res?.list) ? res.list : []).map(normalizeQuestion)
  } catch (error) {
    allItems.value = []
    uni.showToast({ title: error?.message || '江苏题库加载失败', icon: 'none' })
  } finally {
    loading.value = false
  }
}

function goPractice(item) {
  if (!item?.id) return
  const url = `/pages/exam/prepare?source=jiangsu&mode=free&questionId=${encodeURIComponent(item.id)}`
  if (!promptLoginForAction('开始江苏分岗刷题', url)) return
  uni.navigateTo({ url })
}
</script>

<style scoped>
.job-hero {
  background: linear-gradient(135deg, #ffffff 0%, #edf7ff 100%);
}

.job-hero__eyebrow,
.job-hero__title,
.job-hero__desc,
.job-hero__tag {
  display: block;
}

.job-hero__eyebrow {
  color: #2F7FD6;
  font-size: 24rpx;
  font-weight: 700;
}

.job-hero__title {
  margin-top: 10rpx;
  color: #172033;
  font-size: 40rpx;
  font-weight: 900;
}

.job-hero__desc {
  margin-top: 8rpx;
  color: #64748B;
  font-size: 25rpx;
}

.job-hero__tag {
  align-self: flex-start;
  margin-top: 18rpx;
  padding: 8rpx 18rpx;
  border-radius: 999rpx;
  background: #EAF5FF;
  color: #2F7FD6;
  font-size: 23rpx;
  font-weight: 700;
}

.filter-card {
  padding-bottom: 10rpx;
}

.filter-block {
  margin-bottom: 22rpx;
}

.filter-block__label {
  display: block;
  margin-bottom: 14rpx;
  color: #172033;
  font-size: 27rpx;
  font-weight: 800;
}

.filter-scroll {
  width: 100%;
  white-space: nowrap;
}

.filter-scroll__inner {
  display: inline-flex;
  gap: 14rpx;
  padding-bottom: 4rpx;
}

.question-card__meta {
  display: flex;
  flex-wrap: wrap;
  gap: 10rpx;
  margin-bottom: 14rpx;
}

.question-card__meta text {
  padding: 6rpx 14rpx;
  border-radius: 999rpx;
  background: #F6FAFE;
  color: #45617e;
  font-size: 22rpx;
}

.question-card__title,
.question-card__stem {
  display: block;
}

.question-card__title {
  color: #172033;
  font-size: 30rpx;
  font-weight: 800;
  line-height: 1.5;
}

.question-card__stem {
  margin-top: 10rpx;
  color: #64748B;
  font-size: 25rpx;
  line-height: 1.6;
}

.question-card__button {
  margin-top: 20rpx;
}
</style>
