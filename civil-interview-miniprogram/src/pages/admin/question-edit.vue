<template>
  <view class="page">
    <text class="page-title">{{ isEdit ? '编辑题目' : '新增题目' }}</text>
    <text class="page-desc">题干、题型、省份和采分点会直接写入后端题库。</text>

    <view v-if="!userStore.isAdmin" class="card">
      <EmptyState title="无管理员权限" desc="请使用管理员账号登录后再访问。" />
    </view>

    <template v-else>
      <view class="card">
        <text class="form-label">题干</text>
        <textarea v-model="form.stem" class="textarea-field" placeholder="请输入题干" />

        <text class="form-label">题型</text>
        <picker :range="categoryNames" :value="categoryIndex" @change="onCategoryChange">
          <view class="picker-field">{{ selectedCategoryName }}</view>
        </picker>

        <text class="form-label">省份</text>
        <picker :range="provinceNames" :value="provinceIndex" @change="onProvinceChange">
          <view class="picker-field">{{ selectedProvinceName }}</view>
        </picker>

        <view class="time-grid">
          <view>
            <text class="form-label">准备秒数</text>
            <input v-model="form.prepTime" class="field" type="number" />
          </view>
          <view>
            <text class="form-label">作答秒数</text>
            <input v-model="form.answerTime" class="field" type="number" />
          </view>
        </view>

        <text class="form-label">采分点</text>
        <textarea v-model="scoringText" class="textarea-field" placeholder="每行一个采分点，分值可用 | 分隔" />

        <text class="form-label">关键词</text>
        <input v-model="keywordText" class="field" placeholder="多个关键词用逗号分隔" />
      </view>

      <button class="primary-button" :loading="saving" @tap="submitForm">{{ isEdit ? '保存修改' : '新增题目' }}</button>
    </template>
  </view>
</template>

<script setup>
import { computed, reactive, ref } from 'vue'
import { onLoad, onShow } from '@dcloudio/uni-app'
import EmptyState from '../../components/EmptyState.vue'
import { createQuestion, getQuestionById, updateQuestion } from '../../api/questionBank'
import { useUserStore } from '../../stores/user'
import { PROVINCES, QUESTION_CATEGORIES } from '../../utils/constants'
import { hideLoading, requireLogin, showLoading, toast } from '../../utils/navigation'

const userStore = useUserStore()
const questionId = ref('')
const saving = ref(false)
const scoringText = ref('')
const keywordText = ref('')
const form = reactive({
  stem: '',
  dimension: 'analysis',
  province: 'national',
  prepTime: 90,
  answerTime: 180,
  position: '',
  examCategory: '',
  examSubcategory: '',
  system: '',
  positionType: '',
  portalTags: [],
  displayPortals: []
})
const categoryOptions = QUESTION_CATEGORIES.filter((item) => item.key)
const categoryNames = computed(() => categoryOptions.map((item) => item.name))
const provinceOptions = computed(() => userStore.provinces.length ? userStore.provinces : PROVINCES)
const provinceNames = computed(() => provinceOptions.value.map((item) => item.name))
const categoryIndex = computed(() => Math.max(0, categoryOptions.findIndex((item) => item.key === form.dimension)))
const provinceIndex = computed(() => Math.max(0, provinceOptions.value.findIndex((item) => item.code === form.province)))
const selectedCategoryName = computed(() => categoryOptions[categoryIndex.value]?.name || '综合分析')
const selectedProvinceName = computed(() => provinceOptions.value[provinceIndex.value]?.name || '国考')
const isEdit = computed(() => !!questionId.value)

onLoad((query) => {
  questionId.value = query?.id || ''
  if (!questionId.value) applyTargetDefaultsFromQuery(query || {})
})

onShow(async () => {
  if (!requireLogin()) return
  await userStore.loadUserInfo().catch(() => null)
  await userStore.loadProvinces().catch(() => null)
  if (userStore.isAdmin && questionId.value) loadQuestion()
})

function onCategoryChange(event) {
  const selected = categoryOptions[Number(event.detail.value)]
  form.dimension = selected?.key || 'analysis'
}

function onProvinceChange(event) {
  const selected = provinceOptions.value[Number(event.detail.value)]
  form.province = selected?.code || 'national'
}

function scoringToText(points = []) {
  return points
    .map((point) => {
      const content = point?.content || point?.name || ''
      const score = point?.score ?? ''
      return score === '' ? content : `${content}|${score}`
    })
    .filter(Boolean)
    .join('\n')
}

function parseScoringPoints() {
  return scoringText.value
    .split('\n')
    .map((line) => line.trim())
    .filter(Boolean)
    .map((line) => {
      const [content, score] = line.split('|')
      return {
        content: String(content || '').trim(),
        score: Number(score || 0)
      }
    })
}

function parseKeywords() {
  const scoring = keywordText.value
    .split(/[,，\n]/)
    .map((item) => item.trim())
    .filter(Boolean)
  return {
    scoring,
    deducting: [],
    bonus: []
  }
}

async function loadQuestion() {
  showLoading('加载题目')
  try {
    const question = await getQuestionById(questionId.value)
    form.stem = question?.stem || ''
    form.dimension = question?.dimension || 'analysis'
    form.province = question?.province || 'national'
    form.prepTime = Number(question?.prepTime || 90)
    form.answerTime = Number(question?.answerTime || 180)
    form.position = question?.position || ''
    form.examCategory = question?.examCategory || ''
    form.examSubcategory = question?.examSubcategory || ''
    form.system = question?.system || ''
    form.positionType = question?.positionType || ''
    form.portalTags = Array.isArray(question?.portalTags) ? question.portalTags : []
    form.displayPortals = Array.isArray(question?.displayPortals) ? question.displayPortals : []
    scoringText.value = scoringToText(question?.scoringPoints || [])
    keywordText.value = Array.isArray(question?.keywords?.scoring) ? question.keywords.scoring.join('，') : ''
  } catch (error) {
    toast(error?.message || '题目加载失败')
  } finally {
    hideLoading()
  }
}

function applyTargetDefaultsFromQuery(query = {}) {
  const portalTag = String(query.portalTag || query.displayPortal || '').trim()
  form.province = String(query.province || form.province || 'national')
  form.position = String(query.position || '')
  form.examCategory = String(query.examCategory || '')
  form.examSubcategory = String(query.examSubcategory || '')
  form.system = String(query.system || '')
  form.positionType = String(query.positionType || '')
  form.portalTags = portalTag ? [portalTag] : []
  form.displayPortals = portalTag ? [portalTag] : []
}

function buildPayload() {
  const portalTags = Array.isArray(form.portalTags) ? form.portalTags.filter(Boolean) : []
  return {
    stem: form.stem.trim(),
    dimension: form.dimension || 'analysis',
    province: form.province === 'all' ? 'national' : form.province || 'national',
    prepTime: Math.max(30, Number(form.prepTime || 90)),
    answerTime: Math.max(60, Number(form.answerTime || 180)),
    scoringPoints: parseScoringPoints(),
    keywords: parseKeywords(),
    position: form.position || '',
    examCategory: form.examCategory || '',
    examSubcategory: form.examSubcategory || '',
    system: form.system || '',
    positionType: form.positionType || '',
    portalTags,
    displayPortals: portalTags
  }
}

async function submitForm() {
  const payload = buildPayload()
  if (!payload.stem) {
    toast('请填写题干')
    return
  }
  saving.value = true
  try {
    if (isEdit.value) {
      await updateQuestion(questionId.value, payload)
      toast('题目已更新', 'success')
    } else {
      const created = await createQuestion(payload)
      questionId.value = created?.id || ''
      toast('题目已新增', 'success')
    }
    setTimeout(() => {
      uni.navigateBack()
    }, 500)
  } catch (error) {
    toast(error?.message || '保存失败')
  } finally {
    saving.value = false
  }
}
</script>

<style scoped>
.picker-field {
  display: flex;
  align-items: center;
  min-height: 88rpx;
  padding: 0 24rpx;
  border: 1rpx solid #d9e3ef;
  border-radius: 14rpx;
  background: #ffffff;
  color: #1a1a2e;
  font-size: 28rpx;
}

.time-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 16rpx;
}
</style>
