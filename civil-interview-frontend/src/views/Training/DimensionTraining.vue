<template>
  <div class="dim-training page-container">
    <div class="dim-training__header">
      <a-button type="text" @click="$router.back()">
        <LeftOutlined /> 返回
      </a-button>
      <h2>{{ dimensionName }}训练</h2>
    </div>

    <!-- 维度进度 -->
    <div class="card dim-progress">
      <div class="dim-progress__icon" :style="{ background: dimBgColor }">{{ dimIcon }}</div>
      <div class="dim-progress__info">
        <div class="dim-progress__stats">
          <span>练习 <strong>{{ progress.attempts }}</strong> 次</span>
          <span>最佳 <strong>{{ progress.bestScore }}</strong> 分</span>
          <span>平均 <strong>{{ avgScore }}</strong> 分</span>
        </div>
        <div v-if="progress.recentScores.length" class="dim-progress__recent">
          近期得分：
          <span v-for="(s, i) in progress.recentScores.slice(-5)" :key="i" class="recent-score">{{ s }}</span>
        </div>
      </div>
    </div>

    <!-- 定向筛选 -->
    <div class="card dim-filters" v-if="!readonlyMode">
      <h4 style="margin-bottom: 12px; font-size: 14px; color: #555">定向筛选（可选）</h4>
      <a-space direction="vertical" style="width: 100%">
        <a-row :gutter="12">
          <a-col :span="12">
            <a-select v-model:value="selectedExamCategoryId" placeholder="考试大类" allow-clear
              @change="handleExamCategoryFilterChange" style="width: 100%">
              <a-select-option v-for="cat in examCategoryOptions" :key="cat.id" :value="cat.id">
                {{ cat.name }}
              </a-select-option>
            </a-select>
          </a-col>
          <a-col :span="12">
            <a-select v-model:value="selectedRegionId" placeholder="地区" allow-clear
              :disabled="!regionOptions.length" @change="handleRegionFilterChange" style="width: 100%">
              <a-select-option v-for="r in regionOptions" :key="r.id" :value="r.id">
                {{ r.name }}
              </a-select-option>
            </a-select>
          </a-col>
        </a-row>
        <a-row :gutter="12" v-if="hasDirectionOptions">
          <a-col :span="12">
            <a-select v-model:value="selectedDirectionId" placeholder="方向" allow-clear style="width: 100%">
              <a-select-option v-for="d in directionOptions" :key="d.id" :value="d.id">
                {{ d.name }}
              </a-select-option>
            </a-select>
          </a-col>
        </a-row>
        <a-row :gutter="12">
          <a-col :span="24">
            <a-select v-model:value="selectedYearsFilter" mode="multiple" placeholder="年份不限" allow-clear
              :max-tag-count="2" style="width: 100%">
              <a-select-option v-for="y in YEAR_OPTIONS" :key="y" :value="y">{{ y }}</a-select-option>
            </a-select>
          </a-col>
        </a-row>
      </a-space>
    </div>

    <!-- 生成训练题 -->
    <div class="dim-actions">
      <a-button
        type="primary"
        size="large"
        block
        :loading="generating"
        @click="generateQuestions"
      >
        <ThunderboltOutlined /> 生成{{ dimensionName }}题
      </a-button>
    </div>

    <!-- 题目列表 -->
    <div v-if="questions.length" class="dim-questions">
      <div class="section-header">
        <h3>训练题目</h3>
        <a-button type="link" size="small" @click="generateQuestions">重新生成</a-button>
      </div>
      <div
        v-for="(q, idx) in questions"
        :key="q.id"
        class="card question-item"
        @click="startPractice(q)"
      >
        <div class="question-item__idx">{{ idx + 1 }}</div>
        <div class="question-item__content">
          <QuestionMetaTags :question="q" compact :max-keywords="4" />
          <div class="question-item__stem">{{ q.stem }}</div>
        </div>
        <RightOutlined class="question-item__arrow" />
      </div>
    </div>

    <!-- 提示 -->
    <div class="card dim-tip" v-if="tip">
      <BulbOutlined style="color: #D48806; margin-right: 6px" />
      <span>{{ tip }}</span>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { LeftOutlined, ThunderboltOutlined, RightOutlined, BulbOutlined } from '@ant-design/icons-vue'
import { message } from 'ant-design-vue'
import { TRAINING_CATEGORY_TIPS, getTrainingCategory, mergeTrainingProgress } from '@/utils/constants'
import { useTrainingStore } from '@/stores/training'
import { useUserStore } from '@/stores/user'
import { useBillingStore } from '@/stores/billing'
import { generateTrainingQuestions } from '@/api/training'
import QuestionMetaTags from '@/components/common/QuestionMetaTags.vue'
import { getScoringUnavailableMessage, isQuestionScoringSupported } from '@/utils/scoringSupport'
import { DEFAULT_TARGETED_POSITION_TREE } from '@/utils/targetedOptions'
import { YEAR_OPTIONS } from '@/utils/constants'
import { hasPremiumAccess } from '@/utils/access'

const route = useRoute()
const router = useRouter()
const trainingStore = useTrainingStore()
const userStore = useUserStore()
const billingStore = useBillingStore()
const readonlyMode = computed(() => !hasPremiumAccess(userStore, billingStore))

const categoryKey = computed(() => String(route.params.dimension || ''))
const categoryInfo = computed(() => getTrainingCategory(categoryKey.value))
const dimensionName = computed(() => categoryInfo.value?.name || categoryKey.value)
const tip = computed(() => TRAINING_CATEGORY_TIPS[dimensionName.value] || '')
const dimIcon = computed(() => categoryInfo.value?.icon || '📝')
const dimBgColor = computed(() => categoryInfo.value?.bgColor || '#F0F0F0')

const progress = computed(() => {
  if (!categoryInfo.value) {
    return mergeTrainingProgress([])
  }

  return mergeTrainingProgress(
    categoryInfo.value.progressKeys.map((progressKey) => trainingStore.getDimensionProgress(progressKey))
  )
})

const avgScore = computed(() => {
  const p = progress.value
  if (p.attempts === 0) return 0
  return Math.round(p.totalScore / p.attempts)
})

const generating = ref(false)
const questions = ref([])

// Targeted filter state
const selectedExamCategoryId = ref('')
const selectedRegionId = ref('')
const selectedDirectionId = ref('')
const selectedYearsFilter = ref([])
const examCategoryOptions = computed(() =>
  DEFAULT_TARGETED_POSITION_TREE.map(cat => ({ id: cat.id, name: cat.name }))
)
const selectedCategoryNode = computed(() =>
  selectedExamCategoryId.value
    ? DEFAULT_TARGETED_POSITION_TREE.find(c => String(c.id) === String(selectedExamCategoryId.value)) || null
    : null
)
const regionOptions = computed(() =>
  selectedCategoryNode.value?.children || []
)
const selectedRegionNode = computed(() =>
  selectedRegionId.value
    ? regionOptions.value.find(r => String(r.id) === String(selectedRegionId.value)) || null
    : null
)
const hasDirectionOptions = computed(() =>
  (selectedRegionNode.value?.children?.length || 0) > 0
)
const directionOptions = computed(() =>
  selectedRegionNode.value?.children || []
)
const selectedDirectionNode = computed(() =>
  selectedDirectionId.value
    ? directionOptions.value.find(d => String(d.id) === String(selectedDirectionId.value)) || null
    : null
)
function handleExamCategoryFilterChange() {
  selectedRegionId.value = ''
  selectedDirectionId.value = ''
}
function handleRegionFilterChange() {
  selectedDirectionId.value = ''
}

async function generateQuestions() {
  if (!categoryInfo.value) return
  generating.value = true
  try {
    const params = { dimension: categoryInfo.value.requestDimension, count: 3 }
    // Build target filters from selection
    const cat = selectedCategoryNode.value
    const region = selectedRegionNode.value
    const dir = selectedDirectionNode.value
    if (cat) {
      params.examCategory = cat.examCategory || cat.name
    }
    if (region) {
      params.province = region.province || userStore.selectedProvince || 'national'
      if (region.examSubcategory) params.examSubcategory = region.examSubcategory
      params.subcategory = region.subcategory || region.name
    }
    if (dir) {
      params.subcategory2 = dir.subcategory || dir.name
      if (dir.province) params.province = dir.province
    }
    if (selectedYearsFilter.value.length) {
      params.year = selectedYearsFilter.value
    }
    if (!params.province) {
      params.province = userStore.selectedProvince || 'national'
    }
    const generatedQuestions = await generateTrainingQuestions(params)
    questions.value = generatedQuestions.map((question) => ({
      ...question,
      trainingCategoryKey: categoryInfo.value.key,
      trainingCategoryName: categoryInfo.value.name
    }))
  } finally {
    generating.value = false
  }
}

function startPractice(question) {
  if (!isQuestionScoringSupported(question)) {
    message.warning(getScoringUnavailableMessage(1))
    return
  }

  // 暂存题目到 sessionStorage，因为动态生成的题目不在后端题库中
  sessionStorage.setItem('training_question', JSON.stringify(question))
  router.push({ path: '/exam/prepare', query: { questionId: question.id, source: 'training' } })
}

onMounted(() => {
  if (!categoryInfo.value) {
    router.replace('/training')
  }
})
</script>

<style lang="less" scoped>
@import '@/styles/variables.less';

.dim-training__header {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 16px;

  h2 {
    font-size: @font-size-xl;
    color: @text-primary;
    margin: 0;
  }
}

.dim-progress {
  display: flex;
  align-items: center;
  padding: 16px;
  margin-bottom: 16px;
}

.dim-progress__icon {
  width: 56px;
  height: 56px;
  border-radius: 14px;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 28px;
  flex-shrink: 0;
  margin-right: 16px;
}

.dim-progress__info {
  flex: 1;
}

.dim-progress__stats {
  display: flex;
  gap: 16px;
  font-size: @font-size-sm;
  color: @text-secondary;
  margin-bottom: 6px;

  strong {
    color: @primary-color;
    font-weight: 600;
  }
}

.dim-progress__recent {
  font-size: @font-size-xs;
  color: @text-secondary;
}

.recent-score {
  display: inline-block;
  padding: 1px 6px;
  margin-left: 4px;
  border-radius: 4px;
  background: @bg-light-blue;
  color: @primary-color;
  font-size: @font-size-xs;
  font-weight: 500;
}

.dim-actions {
  margin-bottom: 16px;
}

.dim-questions {
  margin-bottom: 16px;
}

.section-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 10px;

  h3 {
    font-size: @font-size-lg;
    color: @text-primary;
    margin: 0;
  }
}

.question-item {
  display: flex;
  align-items: center;
  padding: 14px 16px;
  margin-bottom: 8px;
  cursor: pointer;
  transition: box-shadow 0.2s;

  &:hover {
    box-shadow: @shadow-popup;
  }
}

.question-item__idx {
  width: 28px;
  height: 28px;
  border-radius: 50%;
  background: @bg-light-blue;
  color: @primary-color;
  font-weight: 600;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
  margin-right: 12px;
  font-size: @font-size-sm;
}

.question-item__content {
  flex: 1;
  min-width: 0;
}

.question-item__stem {
  margin-top: 8px;
  font-size: @font-size-base;
  color: @text-regular;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
}

.question-item__arrow {
  color: @text-secondary;
  margin-left: 8px;
  flex-shrink: 0;
}

.dim-tip {
  display: flex;
  align-items: flex-start;
  padding: 14px 16px;
  font-size: @font-size-sm;
  color: @text-regular;
  line-height: 1.5;
}
</style>
