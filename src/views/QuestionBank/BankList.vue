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
          placeholder="题目分类"
          allow-clear
          style="width: 140px"
          @change="onFilterChange"
        >
          <a-select-option v-for="item in questionCategoryOptions" :key="item.key" :value="item.key">
            {{ item.name }}
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
            <QuestionMetaTags :question="q" emphasis :max-keywords="5" />
            <span class="bank-list__item-points">
              {{ q.scoringPoints?.length || 0 }} 个采分点
            </span>
          </div>
          <div class="bank-list__item-stem">
            <QuestionRichContent :text="q.stem" :collapsed-height="128" />
          </div>
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
import ProvinceSelector from '@/components/common/ProvinceSelector.vue'
import EmptyState from '@/components/common/EmptyState.vue'
import QuestionMetaTags from '@/components/common/QuestionMetaTags.vue'
import QuestionRichContent from '@/components/common/QuestionRichContent.vue'
import { message } from 'ant-design-vue'

const bankStore = useQuestionBankStore()
const dimensionFilter = ref(undefined)
const keyword = ref('')
const questionCategoryOptions = [
  { key: 'analysis', name: '综合分析' },
  { key: 'practical', name: '组织管理' },
  { key: 'emergency', name: '应急应变' },
  { key: 'logic', name: '人际沟通' },
  { key: 'expression', name: '现场模拟' },
  { key: 'legal', name: '职业认知' }
]

onMounted(() => {
  bankStore.fetchQuestions()
})

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
  align-items: flex-start;
  gap: 12px;
  margin-bottom: 8px;
}

.bank-list__item-points {
  font-size: @font-size-xs;
  color: @text-secondary;
  margin-left: auto;
  white-space: nowrap;
}

.bank-list__item-stem {
  margin-top: 10px;
}

.bank-list__item-stem :deep(.question-rich-content__body) {
  color: @text-regular;
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
