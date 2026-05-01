<template>
  <div class="smart-rec card">
    <h3 class="smart-rec__title">
      <BulbOutlined /> 智能推荐练习
    </h3>

    <template v-if="weakDimensions.length">
      <a-spin :spinning="loadingRec">
        <div v-if="recommendations.length" class="smart-rec__list">
          <div
            v-for="item in recommendations"
            :key="item.id"
            class="smart-rec__item"
          >
            <div class="smart-rec__item-header">
              <a-tag :color="dimensionColor(item.dimension)">{{ dimensionName(item.dimension) }}</a-tag>
              <span class="smart-rec__reason">{{ item.reason }}</span>
            </div>
            <QuestionMetaTags :question="item" emphasis :max-keywords="5" />
            <div class="smart-rec__stem">
              <QuestionRichContent
                :text="item.stem"
                compact
                :collapsed-height="110"
              />
            </div>
            <div class="smart-rec__footer">
              <span class="smart-rec__difficulty">
                难度：{{ '★'.repeat(item.difficulty) }}{{ '☆'.repeat(5 - item.difficulty) }}
              </span>
              <a-button type="primary" size="small" @click="startPractice(item)">
                开始练习
              </a-button>
            </div>
          </div>
        </div>
        <a-empty v-else-if="!loadingRec" description="暂无推荐题目" :image="false" />
      </a-spin>
    </template>
    <template v-else>
      <div class="smart-rec__balanced">
        <CheckCircleOutlined style="font-size: 32px; color: #389E0D" />
        <p>各维度表现均衡，继续保持！</p>
      </div>
    </template>
  </div>
</template>

<script setup>
import { ref, watch, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { message } from 'ant-design-vue'
import { BulbOutlined, CheckCircleOutlined } from '@ant-design/icons-vue'
import { getQuestions } from '@/api/questionBank'
import { DIMENSIONS } from '@/utils/constants'
import { useDebounce } from '@/composables/useDebounce'
import QuestionMetaTags from '@/components/common/QuestionMetaTags.vue'
import QuestionRichContent from '@/components/common/QuestionRichContent.vue'
import { getScoringUnavailableMessage, isQuestionScoringSupported } from '@/utils/scoringSupport'

const props = defineProps({
  weakDimensions: { type: Array, default: () => [] }
})

const router = useRouter()
const loadingRec = ref(false)
const recommendations = ref([])

const dimMap = Object.fromEntries(DIMENSIONS.map(d => [d.key, d]))

function dimensionName(key) {
  return dimMap[key]?.name || key
}

function dimensionColor(key) {
  const colors = {
    legal: '#1B5FAA',
    practical: '#389E0D',
    logic: '#722ED1',
    expression: '#D48806',
    analysis: '#13C2C2',
    emergency: '#CF1322'
  }
  return colors[key] || '#8C8C8C'
}

async function fetchRecommendations() {
  if (!props.weakDimensions.length) {
    recommendations.value = []
    return
  }
  loadingRec.value = true
  try {
    const results = []
    for (const dim of props.weakDimensions.slice(0, 3)) {
      const res = await getQuestions({ dimension: dim, pageSize: 2 })
      const list = res.list || res || []
      for (const q of list) {
        if (!isQuestionScoringSupported(q)) continue
        const difficulty = Math.min(5, Math.max(1, (q.scoringPoints?.length || 3)))
        results.push({
          id: q.id,
          stem: q.stem,
          dimension: q.dimension || dim,
          difficulty,
          reason: `${dimensionName(dim)}维度薄弱，推荐专项练习`
        })
      }
    }
    recommendations.value = results.slice(0, 6)
  } catch (e) {
    recommendations.value = []
  } finally {
    loadingRec.value = false
  }
}

const { run: debouncedFetch } = useDebounce(fetchRecommendations, 500)

function startPractice(item) {
  if (!isQuestionScoringSupported(item)) {
    message.warning(getScoringUnavailableMessage(1))
    return
  }

  router.push({ path: '/exam/prepare', query: { questionId: item.id } })
}

onMounted(() => {
  fetchRecommendations()
})

watch(() => props.weakDimensions, () => {
  debouncedFetch()
}, { deep: true })
</script>

<style lang="less" scoped>
@import '@/styles/variables.less';

.smart-rec {
  margin-top: 16px;
  padding: 16px;
}

.smart-rec__title {
  font-size: @font-size-lg;
  color: @text-primary;
  margin-bottom: 16px;
}

.smart-rec__item {
  padding: 14px;
  background: linear-gradient(180deg, #ffffff 0%, #f7fbff 100%);
  border-radius: 16px;
  margin-bottom: 10px;
  border: 1px solid rgba(27, 95, 170, 0.08);
  box-shadow: 0 10px 22px rgba(21, 66, 126, 0.06);
}

.smart-rec__item-header {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 8px;
}

.smart-rec__reason {
  font-size: @font-size-xs;
  color: @text-secondary;
}

.smart-rec__stem {
  margin: 10px 0 12px;
}

.smart-rec__stem :deep(.question-rich-content__body) {
  color: @text-regular;
}

.smart-rec__footer {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 12px;
}

.smart-rec__difficulty {
  font-size: @font-size-xs;
  color: @score-gold;
}

.smart-rec__balanced {
  text-align: center;
  padding: 24px 0;

  p {
    margin-top: 8px;
    color: @text-secondary;
    font-size: @font-size-base;
  }
}
</style>
