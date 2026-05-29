<template>
  <div class="jiangsu-job-page page-container">
    <div class="jiangsu-job-hero card">
      <a-button type="link" class="jiangsu-job-hero__back" @click="$router.push('/')">
        返回首页
      </a-button>
      <div class="jiangsu-job-hero__main">
        <div>
          <div class="jiangsu-job-hero__eyebrow">2026 江苏事业单位统考</div>
          <h1>{{ category.title }}</h1>
          <p>{{ categoryMeta }}</p>
        </div>
        <a-tag color="blue">{{ category.hot }}</a-tag>
      </div>
    </div>

    <div class="jiangsu-job-filters card">
      <div class="filter-row">
        <span class="filter-row__label">地市</span>
        <a-radio-group v-model:value="filters.city" size="small">
          <a-radio-button v-for="city in JIANGSU_CITY_FILTERS" :key="city.key" :value="city.key">
            {{ city.name }}
          </a-radio-button>
        </a-radio-group>
      </div>
      <div class="filter-row">
        <span class="filter-row__label">年份</span>
        <a-radio-group v-model:value="filters.year" size="small">
          <a-radio-button value="">全部</a-radio-button>
          <a-radio-button v-for="year in JIANGSU_YEAR_FILTERS" :key="year" :value="year">
            {{ year }}
          </a-radio-button>
        </a-radio-group>
      </div>
      <div class="filter-row">
        <span class="filter-row__label">题型</span>
        <a-radio-group v-model:value="filters.type" size="small">
          <a-radio-button value="">全部</a-radio-button>
          <a-radio-button v-for="type in JIANGSU_QUESTION_TYPES" :key="type.key" :value="type.key">
            {{ type.name }}
          </a-radio-button>
        </a-radio-group>
      </div>
    </div>

    <div class="jiangsu-job-list">
      <div class="jiangsu-job-list__head">
        <h2>题目列表</h2>
        <span>{{ listStatusText }}</span>
      </div>

      <a-spin :spinning="loading">
      <div v-if="filteredItems.length">
        <div v-for="item in filteredItems" :key="item.id" class="jiangsu-question-card card">
          <div class="jiangsu-question-card__top">
            <a-tag color="blue">{{ item.yearLabel }}</a-tag>
            <a-tag>{{ item.cityName }}</a-tag>
            <a-tag color="green">{{ item.typeName }}</a-tag>
          </div>
          <h3>{{ item.title }}</h3>
          <p>{{ item.stem }}</p>
          <div class="jiangsu-question-card__actions">
            <a-button type="primary" size="small" @click="startPractice(item)">
              开始刷题
            </a-button>
            <a-button size="small" @click="$router.push({ path: '/bank', query: { province: 'jiangsu', examCategory: '事业单位考试' } })">去题库筛选</a-button>
          </div>
        </div>
      </div>
      <EmptyState v-else :text="emptyText" />
      </a-spin>
    </div>
  </div>
</template>

<script setup>
import { computed, onMounted, reactive, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import EmptyState from '@/components/common/EmptyState.vue'
import {
  JIANGSU_CITY_FILTERS,
  JIANGSU_QUESTION_TYPES,
  JIANGSU_YEAR_FILTERS,
  getJiangsuJobCategory
} from '@/utils/jiangsuJobs'
import { getQuestions } from '@/api/questionBank'
import { message } from 'ant-design-vue'

const route = useRoute()
const router = useRouter()
const category = computed(() => getJiangsuJobCategory(String(route.params.category || 'a')))
const categoryMeta = computed(() => [category.value.scope, category.value.subtitle].filter(Boolean).join(' · '))
const filters = reactive({
  city: 'provincial',
  year: '',
  type: ''
})
const loading = ref(false)
const allItems = ref([])
const listStatusText = computed(() => (loading.value ? '正在加载真实题库...' : `真实题库 · ${filteredItems.value.length} 题`))
const emptyText = computed(() => '暂无匹配题目，请调整筛选条件')
const filteredItems = computed(() => allItems.value.filter((item) => {
  if (filters.city !== 'all' && item.cityKey !== filters.city) return false
  if (filters.year && item.year !== filters.year) return false
  if (filters.type && item.typeKey !== filters.type) return false
  return true
}))

function normalizeQuestion(item = {}) {
  const meta = item.keywords?._meta || item.keywords || {}
  const metaYear = Array.isArray(meta.year) ? meta.year[0] : (meta.year || '')
  const metaText = [
    item.sourceDocument,
    item.sourceFile,
    ...(Array.isArray(item.tags) ? item.tags : [])
  ].join(' ')
  const year = metaYear || String(metaText.match(/20\d{2}/)?.[0] || '')
  const city = JIANGSU_CITY_FILTERS.find((option) => option.key !== 'all' && (
    metaText.includes(option.name) || meta.subcategory2 === option.name
  ))
  const type = JIANGSU_QUESTION_TYPES.find((option) => item.dimension === option.key || metaText.includes(option.name))
  return {
    ...item,
    year,
    yearLabel: year || '真题',
    cityKey: city?.key || 'all',
    cityName: city?.name || meta.subcategory2 || '江苏',
    typeKey: type?.key || item.dimension || '',
    typeName: type?.name || '结构化面试',
    title: `${year || '江苏'} · ${city?.name || meta.subcategory2 || '江苏'} · ${category.value.shortTitle} · ${type?.name || '结构化面试'}`
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
    message.error(error?.normalizedMessage || error?.message || '江苏题库加载失败')
  } finally {
    loading.value = false
  }
}

function startPractice(item) {
  if (!item?.id) return
  router.push({
    path: '/exam/prepare',
    query: { source: 'jiangsu', questionId: item.id, mode: 'free' }
  })
}

watch(() => route.params.category, () => {
  filters.city = 'provincial'
  filters.year = ''
  filters.type = ''
  loadQuestions()
})

onMounted(loadQuestions)
</script>

<style lang="less" scoped>
@import '@/styles/variables.less';

.jiangsu-job-hero {
  padding: 20px;
  border: 1px solid fade(@primary-color, 10%);
  background: linear-gradient(135deg, #ffffff 0%, #edf7ff 100%);
}

.jiangsu-job-hero__back {
  padding: 0;
  margin-bottom: 10px;
}

.jiangsu-job-hero__main {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 16px;

  h1 {
    margin: 4px 0;
    color: @text-primary;
    font-size: @font-size-xxl;
  }

  p {
    margin: 0;
    color: @text-secondary;
    font-size: @font-size-sm;
  }
}

.jiangsu-job-hero__eyebrow {
  color: @primary-color;
  font-size: @font-size-sm;
  font-weight: 600;
}

.jiangsu-job-filters {
  margin-top: 12px;
  padding: 14px 16px;
}

.filter-row {
  display: grid;
  grid-template-columns: 52px minmax(0, 1fr);
  gap: 10px;
  align-items: flex-start;
  padding: 8px 0;

  :deep(.ant-radio-group) {
    display: flex;
    flex-wrap: wrap;
    gap: 8px;
  }

  :deep(.ant-radio-button-wrapper) {
    border-radius: 6px;
    border-inline-start-width: 1px;
  }

  :deep(.ant-radio-button-wrapper::before) {
    display: none;
  }
}

.filter-row__label {
  color: @text-primary;
  font-size: @font-size-sm;
  font-weight: 600;
  line-height: 24px;
}

.jiangsu-job-list {
  margin-top: 16px;
}

.jiangsu-job-list__head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 10px;

  h2 {
    margin: 0;
    color: @text-primary;
    font-size: @font-size-lg;
  }

  span {
    color: @text-secondary;
    font-size: @font-size-xs;
  }
}

.jiangsu-question-card {
  margin-bottom: 10px;
  padding: 14px 16px;

  h3 {
    margin: 8px 0 6px;
    color: @text-primary;
    font-size: @font-size-base;
    font-weight: 700;
  }

  p {
    margin: 0;
    color: @text-regular;
    font-size: @font-size-sm;
    line-height: 1.7;
  }
}

.jiangsu-question-card__top,
.jiangsu-question-card__actions {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.jiangsu-question-card__actions {
  justify-content: flex-end;
  margin-top: 12px;
}

@media (max-width: 560px) {
  .jiangsu-job-hero__main,
  .jiangsu-job-list__head {
    align-items: flex-start;
    flex-direction: column;
  }

  .filter-row {
    grid-template-columns: 1fr;
  }
}
</style>
