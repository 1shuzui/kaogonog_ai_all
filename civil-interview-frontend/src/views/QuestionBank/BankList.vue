<template>
  <div class="bank-list page-container">
    <div class="bank-list__header">
      <h2>{{ isAdmin ? '题库管理' : '题库' }}</h2>
      <div v-if="isAdmin" class="bank-list__actions">
        <a-button type="primary" @click="$router.push('/bank/import')">
          <UploadOutlined /> 批量导入
        </a-button>
        <a-button @click="$router.push('/bank/edit')">
          <PlusOutlined /> 新增题目
        </a-button>
      </div>
    </div>

    <div v-if="!hasQuestionBankAccess" class="bank-list__access card">
      <h3>题库需开通后查看</h3>
      <p>完整题库、筛选检索和扩展真题属于正式训练内容。你可以先体验 1 道试用题，或开通套餐后继续查看题库。</p>
      <div class="bank-list__access-actions">
        <a-button @click="startTrial">试用 1 题</a-button>
        <a-button type="primary" @click="goPricing">开通套餐</a-button>
      </div>
    </div>

    <template v-else>
      <!-- 筛选栏 -->
      <div class="bank-list__filters card">
        <a-space wrap>
          <ProvinceSelector v-model:value="provinceFilter" @change="onProvinceChange" />
          <a-select
            v-model:value="examCategoryFilter"
            placeholder="考试大类"
            allow-clear
            style="width: 140px"
            @change="onExamCategoryChange"
          >
            <a-select-option v-for="item in EXAM_CATEGORIES" :key="item.code" :value="item.code">
              {{ item.name }}
            </a-select-option>
          </a-select>
          <a-input
            v-model:value="subcategoryFilter"
            :placeholder="subcategoryPlaceholder"
            allow-clear
            style="width: 130px"
          />
          <a-input
            v-model:value="subcategory2Filter"
            placeholder="四级分类"
            allow-clear
            style="width: 130px"
          />
          <a-select
            v-model:value="yearFilter"
            placeholder="年份"
            mode="multiple"
            allow-clear
            style="width: 180px"
            :max-tag-count="2"
          >
            <a-select-option v-for="y in YEAR_OPTIONS" :key="y" :value="y">{{ y }}</a-select-option>
          </a-select>
          <a-select
            v-model:value="dimensionFilter"
            placeholder="题目分类"
            allow-clear
            style="width: 140px"
          >
            <a-select-option v-for="item in questionCategoryOptions" :key="item.key" :value="item.key">
              {{ item.name }}
            </a-select-option>
          </a-select>
          <a-select
            v-if="isAdmin"
            v-model:value="categoryReviewFilter"
            placeholder="分类复核"
            allow-clear
            style="width: 150px"
          >
            <a-select-option value="needs_review">分类待确认</a-select-option>
            <a-select-option value="confirmed">分类已确认</a-select-option>
          </a-select>
          <a-input-search
            v-model:value="keyword"
            placeholder="搜索题目"
            style="width: 200px"
            @search="onFilterChange"
            allow-clear
          />
          <a-button type="primary" @click="onFilterChange">搜索</a-button>
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
              <a-tag v-if="isAdmin && q.categoryReviewStatus === 'needs_review'" color="orange">
                分类待确认
              </a-tag>
              <a-tag v-else-if="isAdmin && q.categoryReviewStatus === 'confirmed'" color="green">
                分类已确认
              </a-tag>
              <span class="bank-list__item-points">
                {{ q.scoringPoints?.length || 0 }} 个采分点
              </span>
            </div>
            <div class="bank-list__item-stem">
              <QuestionRichContent :text="q.stem" :collapsed-height="128" />
            </div>
            <div v-if="isAdmin" class="bank-list__item-footer">
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
        </div>
        <EmptyState v-else text="暂无题目" />
      </a-spin>

      <!-- 分页 -->
      <div class="bank-list__pagination" v-if="bankStore.pagination.total > 10">
        <a-pagination
          v-model:current="bankStore.pagination.current"
          :total="bankStore.pagination.total"
          :page-size="bankStore.pagination.pageSize"
          @change="onPageChange"
          @showSizeChange="onPageChange"
          size="small"
          show-size-changer
          show-less-items
        />
      </div>
    </template>
  </div>
</template>

<script setup>
import { computed, ref, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { UploadOutlined, PlusOutlined } from '@ant-design/icons-vue'
import { useQuestionBankStore } from '@/stores/questionBank'
import { useBillingStore } from '@/stores/billing'
import ProvinceSelector from '@/components/common/ProvinceSelector.vue'
import EmptyState from '@/components/common/EmptyState.vue'
import QuestionMetaTags from '@/components/common/QuestionMetaTags.vue'
import QuestionRichContent from '@/components/common/QuestionRichContent.vue'
import { message } from 'ant-design-vue'
import { useUserStore } from '@/stores/user'
import { EXAM_CATEGORIES, SUBCATEGORY_LABELS, YEAR_OPTIONS } from '@/utils/constants'

const router = useRouter()
const route = useRoute()
const bankStore = useQuestionBankStore()
const billingStore = useBillingStore()
const userStore = useUserStore()
const isAdmin = computed(() => userStore.isAdmin)
const hasQuestionBankAccess = computed(() => (
  isAdmin.value
  || billingStore.isPaid
  || userStore.userInfo?.billing?.isPaid === true
  || userStore.userInfo?.permissions?.canAccessPremiumModules === true
))
const provinceFilter = ref('all')
const examCategoryFilter = ref('')
const subcategoryFilter = ref('')
const subcategory2Filter = ref('')
const yearFilter = ref([])
const dimensionFilter = ref(undefined)
const categoryReviewFilter = ref(undefined)
const keyword = ref('')
const subcategoryPlaceholder = computed(() => {
  if (!examCategoryFilter.value) return '三级分类'
  return SUBCATEGORY_LABELS[examCategoryFilter.value] || '三级分类'
})
const questionCategoryOptions = [
  { key: 'analysis', name: '综合分析' },
  { key: 'practical', name: '组织管理' },
  { key: 'emergency', name: '应急应变' },
  { key: 'logic', name: '人际沟通' },
  { key: 'expression', name: '现场模拟' },
  { key: 'legal', name: '职业认知' }
]

onMounted(async () => {
  await userStore.loadUserInfo().catch(() => null)

  const q = route.query || {}
  provinceFilter.value = q.province || 'all'
  examCategoryFilter.value = q.examCategory || ''
  subcategoryFilter.value = q.subcategory || ''
  subcategory2Filter.value = q.subcategory2 || ''
  yearFilter.value = q.year ? String(q.year).split(',').filter(Boolean) : []
  dimensionFilter.value = q.dimension || undefined
  categoryReviewFilter.value = q.categoryReview || undefined
  keyword.value = q.keyword || ''

  if (hasQuestionBankAccess.value) {
    bankStore.setFilters({
      province: provinceFilter.value === 'all' ? '' : provinceFilter.value || '',
      dimension: dimensionFilter.value || '',
      examCategory: examCategoryFilter.value || '',
      subcategory: subcategoryFilter.value || '',
      subcategory2: subcategory2Filter.value || '',
      year: (yearFilter.value || []).join(','),
      categoryReview: categoryReviewFilter.value || '',
      keyword: keyword.value
    })
    bankStore.fetchQuestions({ page: 1 })
  }
})

function onProvinceChange(value) {
  provinceFilter.value = value
}

function onExamCategoryChange(value) {
  examCategoryFilter.value = value || ''
  subcategoryFilter.value = ''
  subcategory2Filter.value = ''
  onFilterChange()
}

function onFilterChange() {
  if (!hasQuestionBankAccess.value) return
  bankStore.setFilters({
    province: provinceFilter.value === 'all' ? '' : provinceFilter.value || '',
    dimension: dimensionFilter.value || '',
    examCategory: examCategoryFilter.value || '',
    subcategory: subcategoryFilter.value || '',
    subcategory2: subcategory2Filter.value || '',
    year: (yearFilter.value || []).join(','),
    categoryReview: categoryReviewFilter.value || '',
    keyword: keyword.value
  })
  bankStore.fetchQuestions()
}

function onPageChange(page, pageSize) {
  if (!hasQuestionBankAccess.value) return
  bankStore.fetchQuestions({ current: page, pageSize })
}

async function onDelete(id) {
  await bankStore.removeQuestion(id)
  message.success('删除成功')
}

function startTrial() {
  router.push({ path: '/exam/prepare', query: { trial: '1' } })
}

function goPricing() {
  router.push({ path: '/pricing', query: { redirect: '/bank', source: '题库' } })
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

.bank-list__access {
  padding: 18px 20px;
  margin-bottom: 16px;

  h3 {
    color: @text-primary;
    font-size: @font-size-lg;
    margin: 0 0 8px;
  }

  p {
    color: @text-secondary;
    font-size: @font-size-sm;
    line-height: 1.7;
    margin: 0;
  }
}

.bank-list__access-actions {
  display: flex;
  gap: 10px;
  margin-top: 14px;
  flex-wrap: wrap;
}

.bank-list__item {
  margin-bottom: 12px;
  padding: 14px 16px;
  display: flex;
  flex-direction: column;
  gap: 10px;
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
  min-width: 0;
}

.bank-list__item-stem :deep(.question-rich-content__body) {
  color: @text-regular;
}

.bank-list__item-footer {
  margin-top: auto;
  display: flex;
  align-items: center;
  justify-content: flex-end;
  min-height: 32px;
}

.bank-list__item-actions {
  display: flex;
  gap: 8px;
}

.bank-list__pagination {
  display: flex;
  justify-content: center;
  margin-top: 16px;
}
</style>
