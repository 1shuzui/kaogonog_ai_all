<template>
  <div class="bank-list page-container">
    <div class="bank-list__header">
      <h2>题库管理</h2>
      <div class="bank-list__actions">
        <a-button type="primary" @click="$router.push('/bank/import')">
          <UploadOutlined /> 批量导入
        </a-button>
        <a-button @click="$router.push('/bank/edit')">
          <PlusOutlined /> 新增题目
        </a-button>
      </div>
    </div>

    <!-- 筛选栏 -->
    <div class="bank-list__filters card">
      <a-space wrap>
        <ProvinceSelector @change="onProvinceChange" />
        <a-select
          v-model:value="dimensionFilter"
          placeholder="评分维度"
          allow-clear
          style="width: 120px"
          @change="onFilterChange"
        >
          <a-select-option v-for="d in DIMENSIONS" :key="d.key" :value="d.key">
            {{ d.name }}
          </a-select-option>
        </a-select>
        <a-input-search
          v-model:value="keyword"
          placeholder="搜索题目"
          style="width: 200px"
          @search="onFilterChange"
          allow-clear
        />
      </a-space>
    </div>

    <!-- 题目列表 -->
    <a-spin :spinning="bankStore.loading">
      <div class="bank-list__items" v-if="bankStore.questions.length">
        <div
          v-for="q in bankStore.questions"
          :key="q.id"
          class="bank-list__item card"
        >
          <div class="bank-list__item-header">
            <a-tag color="blue">{{ getDimensionName(q.dimension) }}</a-tag>
            <a-tag>{{ getProvinceName(q.province) }}</a-tag>
            <span class="bank-list__item-points">
              {{ q.scoringPoints?.length || 0 }} 个采分点
            </span>
          </div>
          <div class="bank-list__item-stem">{{ q.stem }}</div>
          <div class="bank-list__item-actions">
            <a-button type="link" size="small" @click="$router.push(`/bank/edit/${q.id}`)">
              编辑
            </a-button>
            <a-popconfirm title="确认删除？" @confirm="onDelete(q.id)">
              <a-button type="link" danger size="small">删除</a-button>
            </a-popconfirm>
          </div>
        </div>
      </div>
      <EmptyState v-else text="暂无题目" />
    </a-spin>

    <!-- 分页 -->
    <div class="bank-list__pagination" v-if="bankStore.pagination.total > 10">
      <a-pagination
        v-model:current="bankStore.pagination.current"
        :total="bankStore.pagination.total"
        :pageSize="bankStore.pagination.pageSize"
        @change="onPageChange"
        size="small"
        show-less-items
      />
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { UploadOutlined, PlusOutlined } from '@ant-design/icons-vue'
import { useQuestionBankStore } from '@/stores/questionBank'
import { useUserStore } from '@/stores/user'
import { DIMENSIONS, PROVINCES } from '@/utils/constants'
import ProvinceSelector from '@/components/common/ProvinceSelector.vue'
import EmptyState from '@/components/common/EmptyState.vue'
import { message } from 'ant-design-vue'

const bankStore = useQuestionBankStore()
const userStore = useUserStore()
const dimensionFilter = ref(undefined)
const keyword = ref('')

onMounted(() => {
  bankStore.fetchQuestions()
})

function getDimensionName(key) {
  const d = DIMENSIONS.find(d => d.key === key)
  return d ? d.name : key
}

function getProvinceName(code) {
  const p = PROVINCES.find(p => p.code === code)
  return p ? p.name : code
}

function onProvinceChange(value) {
  bankStore.switchProvince(value === 'all' ? '' : value)
}

function onFilterChange() {
  bankStore.setFilters({ dimension: dimensionFilter.value || '', keyword: keyword.value })
  bankStore.fetchQuestions()
}

function onPageChange(page) {
  bankStore.fetchQuestions({ page })
}

async function onDelete(id) {
  await bankStore.removeQuestion(id)
  message.success('删除成功')
}
</script>

<style lang="less" scoped>
@import '@/styles/variables.less';

.bank-list__header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 16px;

  h2 {
    font-size: @font-size-xl;
    color: @text-primary;
    margin: 0;
  }
}

.bank-list__actions {
  display: flex;
  gap: 8px;
}

.bank-list__filters {
  margin-bottom: 12px;
  padding: 12px 16px;
}

.bank-list__item {
  margin-bottom: 12px;
  padding: 14px 16px;
}

.bank-list__item-header {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 8px;
}

.bank-list__item-points {
  font-size: @font-size-xs;
  color: @text-secondary;
  margin-left: auto;
}

.bank-list__item-stem {
  font-size: @font-size-base;
  color: @text-regular;
  line-height: 1.6;
  display: -webkit-box;
  -webkit-line-clamp: 3;
  -webkit-box-orient: vertical;
  overflow: hidden;
}

.bank-list__item-actions {
  margin-top: 8px;
  display: flex;
  gap: 8px;
  justify-content: flex-end;
}

.bank-list__pagination {
  display: flex;
  justify-content: center;
  margin-top: 16px;
}
</style>
