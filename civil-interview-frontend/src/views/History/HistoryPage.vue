<!--
历史记录页，展示练习记录、筛选和成绩回看，是用户复盘答题表现的入口。

历史记录是个人数据，必须登录后读取；页面只按后端记录筛选和跳转详情，不根据当前题库筛选重新推导成绩。

@param: 无；筛选条件来自页面表单，数据来自 history store。
@return: 渲染历史列表、筛选器、分页和结果回看入口。
@raises: 不主动抛业务异常；未登录、记录缺失或查询失败由请求层和空态提示承接。
-->
<template>
  <div class="history-page page-container">
    <div class="history-page__header">
      <a-button @click="goBack">返回</a-button>
      <h2>历史记录</h2>
    </div>

    <!-- 筛选 -->
    <div class="card" style="padding: 12px 16px; margin-bottom: 12px">
      <a-space wrap>
        <ProvinceSelector v-model:value="provinceFilter" @change="onProvinceChange" />
        <a-range-picker
          v-model:value="dateRange"
          size="small"
          @change="onFilterChange"
        />
      </a-space>
    </div>

    <!-- 列表 -->
    <a-spin :spinning="historyStore.loading">
      <div v-if="historyStore.records.length">
        <div
          v-for="record in historyStore.records"
          :key="record.examId"
          class="history-item card"
          @click="$router.push(`/result/${record.examId}`)"
        >
          <div class="history-item__left">
            <div class="history-item__summary">{{ record.questionSummary }}</div>
            <div class="history-item__meta">
              <span>{{ formatDate(record.date) }}</span>
              <a-tag :color="gradeColor(record.grade)" size="small">{{ record.grade }}</a-tag>
              <span>{{ record.questionCount }} 题</span>
            </div>
            <!-- 维度迷你柱 -->
            <div class="history-item__dims">
              <span
                v-for="dim in record.dimensions"
                :key="dim.name"
                class="mini-dim"
                :title="`${dim.name}: ${dim.score}/${dim.maxScore}`"
              >
                <span
                  class="mini-dim__bar"
                  :style="{ width: (dim.score / dim.maxScore * 100) + '%', background: barColor(dim) }"
                ></span>
              </span>
            </div>
          </div>
          <ScoreRing :score="record.totalScore" :maxScore="record.maxScore" size="small" />
        </div>
      </div>
      <EmptyState v-else text="暂无历史记录" />
    </a-spin>

    <div class="history-pagination" v-if="historyStore.pagination.total > 10">
      <a-pagination
        v-model:current="historyStore.pagination.current"
        :total="historyStore.pagination.total"
        :pageSize="historyStore.pagination.pageSize"
        @change="onPageChange"
        size="small"
        show-less-items
      />
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { useHistoryStore } from '@/stores/history'
import { formatDate } from '@/utils/formatter'
import { GRADE_CONFIG } from '@/utils/constants'
import ProvinceSelector from '@/components/common/ProvinceSelector.vue'
import ScoreRing from '@/components/common/ScoreRing.vue'
import EmptyState from '@/components/common/EmptyState.vue'

const historyStore = useHistoryStore()
const router = useRouter()
const dateRange = ref(null)
const provinceFilter = ref('all')

function gradeColor(grade) {
  return GRADE_CONFIG[grade]?.color || '#8C8C8C'
}

function barColor(dim) {
  const ratio = dim.score / dim.maxScore
  if (ratio >= 0.8) return '#389E0D'
  if (ratio >= 0.6) return '#1B5FAA'
  if (ratio >= 0.4) return '#D48806'
  return '#CF1322'
}

function goBack() {
  if (window.history.length > 1) {
    router.back()
    return
  }
  router.push('/profile')
}

onMounted(() => {
  historyStore.fetchRecords({ page: 1, current: 1 })
})

function onProvinceChange(value) {
  provinceFilter.value = value || 'all'
  historyStore.fetchRecords({ province: provinceFilter.value === 'all' ? '' : provinceFilter.value, page: 1, current: 1 })
}

function onFilterChange() {
  const [start, end] = dateRange.value || []
  historyStore.fetchRecords({
    province: provinceFilter.value === 'all' ? '' : provinceFilter.value,
    startDate: start?.format?.('YYYY-MM-DD') || '',
    endDate: end?.format?.('YYYY-MM-DD') || '',
    page: 1,
    current: 1
  })
}

function onPageChange(page) {
  const [start, end] = dateRange.value || []
  historyStore.fetchRecords({
    page,
    current: page,
    province: provinceFilter.value === 'all' ? '' : provinceFilter.value,
    startDate: start?.format?.('YYYY-MM-DD') || '',
    endDate: end?.format?.('YYYY-MM-DD') || ''
  })
}
</script>

<style lang="less" scoped>
@import '@/styles/variables.less';

.history-page__header {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-bottom: 16px;
}

.history-page h2 {
  font-size: @font-size-xl;
  color: @text-primary;
  margin: 0;
}

.history-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 14px 16px;
  margin-bottom: 8px;
  cursor: pointer;
  transition: box-shadow 0.2s;

  &:hover { box-shadow: @shadow-popup; }
}

.history-item__summary {
  font-size: @font-size-base;
  color: @text-regular;
  margin-bottom: 4px;
  display: -webkit-box;
  -webkit-line-clamp: 1;
  -webkit-box-orient: vertical;
  overflow: hidden;
}

.history-item__meta {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: @font-size-xs;
  color: @text-secondary;
  margin-bottom: 6px;
}

.history-item__dims {
  display: flex;
  gap: 3px;
}

.mini-dim {
  display: inline-block;
  width: 32px;
  height: 4px;
  background: #F0F0F0;
  border-radius: 2px;
  overflow: hidden;
}

.mini-dim__bar {
  display: block;
  height: 100%;
  border-radius: 2px;
}

.history-pagination {
  display: flex;
  justify-content: center;
  margin-top: 16px;
}
</style>
