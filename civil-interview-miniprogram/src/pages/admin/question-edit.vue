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

        <!-- 高级设置切换 -->
        <view class="advanced-toggle" @tap="showAdvanced = !showAdvanced">
          <text class="advanced-toggle__text">高级设置（考试分类、套题、同义词、AI关键词）</text>
          <text class="advanced-toggle__icon">{{ showAdvanced ? '▲' : '▼' }}</text>
        </view>

        <view v-if="showAdvanced" class="advanced-section">
          <text class="form-label">考试大类</text>
          <input v-model="form.examCategory" class="field" placeholder="如：省级公务员考试、事业单位考试" />

          <text class="form-label">二级分类</text>
          <input v-model="form.examSubcategory" class="field" placeholder="如：安徽省、江苏省" />

          <text class="form-label">三级分类</text>
          <input v-model="form.subcategory" class="field" placeholder="如：地级市、系统、岗位方向" />

          <text class="form-label">四级分类</text>
          <input v-model="form.subcategory2" class="field" placeholder="如：区县、具体单位" />

          <view class="time-grid">
            <view>
              <text class="form-label">面试形式</text>
              <input v-model="form.interviewFormat" class="field" placeholder="如：15分钟包干" />
            </view>
            <view>
              <text class="form-label">计时模式</text>
              <input v-model="form.timingMode" class="field" placeholder="如：8分钟读题+12分钟答题" />
            </view>
          </view>

          <text class="form-label">年份（多个用逗号分隔）</text>
          <input v-model="yearText" class="field" placeholder="如：2024,2023,2022" />

          <text class="form-label">套题数量</text>
          <input v-model="form.questionCount" class="field" placeholder="如：3" />

          <view class="time-grid">
            <view>
              <text class="form-label">套题ID</text>
              <input v-model="form.suiteId" class="field" placeholder="如：SD-20200829A-SK" />
            </view>
            <view>
              <text class="form-label">套题Key</text>
              <input v-model="form.suiteKey" class="field" placeholder="同 suiteId" />
            </view>
          </view>

          <text class="form-label">套题名称</text>
          <input v-model="form.suiteName" class="field" placeholder="如：2020年8月31日上午山东省考面试题" />

          <text class="form-label">同义表述库（每行一个）</text>
          <textarea v-model="synonymsText" class="textarea-field" placeholder="每行一个同义表述" />

          <text class="form-label">扣分关键词（逗号分隔）</text>
          <input v-model="deductingText" class="field" placeholder="多个关键词用逗号分隔" />

          <text class="form-label">加分关键词（逗号分隔）</text>
          <input v-model="bonusText" class="field" placeholder="多个关键词用逗号分隔" />
        </view>
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
const showAdvanced = ref(false)
const scoringText = ref('')
const keywordText = ref('')
const yearText = ref('')
const synonymsText = ref('')
const deductingText = ref('')
const bonusText = ref('')

const form = reactive({
  stem: '',
  dimension: 'analysis',
  province: 'national',
  prepTime: 90,
  answerTime: 180,
  position: '',
  examCategory: '',
  examSubcategory: '',
  subcategory: '',
  subcategory2: '',
  system: '',
  positionType: '',
  portalTags: [],
  displayPortals: [],
  interviewFormat: '',
  timingMode: '',
  year: [],
  questionCount: '',
  suiteId: '',
  suiteKey: '',
  suiteName: '',
  synonyms: [],
  keywordsDeducting: [],
  keywordsBonus: []
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
  const deducting = deductingText.value
    .split(/[,，\n]/)
    .map((item) => item.trim())
    .filter(Boolean)
  const bonus = bonusText.value
    .split(/[,，\n]/)
    .map((item) => item.trim())
    .filter(Boolean)
  return {
    scoring,
    deducting,
    bonus
  }
}

function parseSynonyms() {
  return synonymsText.value
    .split('\n')
    .map((item) => item.trim())
    .filter(Boolean)
}

function parseYear() {
  return yearText.value
    .split(/[,，\s]+/)
    .map((item) => item.trim())
    .filter(Boolean)
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
    form.subcategory = question?.subcategory || ''
    form.subcategory2 = question?.subcategory2 || ''
    form.system = question?.system || ''
    form.positionType = question?.positionType || ''
    form.portalTags = Array.isArray(question?.portalTags) ? question.portalTags : []
    form.displayPortals = Array.isArray(question?.displayPortals) ? question.displayPortals : []
    form.interviewFormat = question?.interviewFormat || ''
    form.timingMode = question?.timingMode || ''
    form.year = Array.isArray(question?.year) ? question.year : (question?.year ? String(question.year).split(',').filter(Boolean) : [])
    form.questionCount = question?.questionCount || ''
    form.suiteId = question?.keywords?._meta?.suiteId || question?.suiteId || ''
    form.suiteKey = question?.keywords?._meta?.suiteKey || question?.suiteKey || ''
    form.suiteName = question?.keywords?._meta?.suiteName || question?.suiteName || ''
    form.synonyms = Array.isArray(question?.synonyms) ? question.synonyms : []
    form.keywordsDeducting = Array.isArray(question?.keywords?.deducting) ? question.keywords.deducting : []
    form.keywordsBonus = Array.isArray(question?.keywords?.bonus) ? question.keywords.bonus : []

    scoringText.value = scoringToText(question?.scoringPoints || [])
    keywordText.value = Array.isArray(question?.keywords?.scoring) ? question.keywords.scoring.join('，') : ''
    yearText.value = Array.isArray(form.year) ? form.year.join(',') : ''
    synonymsText.value = form.synonyms.join('\n')
    deductingText.value = form.keywordsDeducting.join('，')
    bonusText.value = form.keywordsBonus.join('，')
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
  form.subcategory = String(query.subcategory || '')
  form.subcategory2 = String(query.subcategory2 || '')
  form.system = String(query.system || '')
  form.positionType = String(query.positionType || '')
  form.portalTags = portalTag ? [portalTag] : []
  form.displayPortals = portalTag ? [portalTag] : []
  form.interviewFormat = String(query.interviewFormat || '')
  form.timingMode = String(query.timingMode || '')
  form.questionCount = String(query.questionCount || '')
  form.suiteId = String(query.suiteId || '')
  form.suiteKey = String(query.suiteKey || '')
  form.suiteName = String(query.suiteName || '')
  yearText.value = query.year ? String(query.year).split(',').filter(Boolean).join(',') : ''
}

function buildPayload() {
  const portalTags = Array.isArray(form.portalTags) ? form.portalTags.filter(Boolean) : []
  const parsedKeywords = parseKeywords()
  const parsedSynonyms = parseSynonyms()
  const parsedYear = parseYear()

  return {
    stem: form.stem.trim(),
    dimension: form.dimension || 'analysis',
    province: form.province === 'all' ? 'national' : form.province || 'national',
    prepTime: Math.max(30, Number(form.prepTime || 90)),
    answerTime: Math.max(60, Number(form.answerTime || 180)),
    scoringPoints: parseScoringPoints(),
    keywords: parsedKeywords,
    position: form.position || '',
    examCategory: form.examCategory || '',
    examSubcategory: form.examSubcategory || '',
    subcategory: form.subcategory || '',
    subcategory2: form.subcategory2 || '',
    system: form.system || '',
    positionType: form.positionType || '',
    portalTags,
    displayPortals: portalTags,
    interviewFormat: form.interviewFormat || '',
    timingMode: form.timingMode || '',
    year: parsedYear,
    questionCount: form.questionCount || '',
    suiteId: form.suiteId || '',
    suiteKey: form.suiteKey || '',
    suiteName: form.suiteName || '',
    synonyms: parsedSynonyms,
    keywordsDeducting: parsedKeywords.deducting,
    keywordsBonus: parsedKeywords.bonus
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

.advanced-toggle {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 28rpx 0 16rpx;
  margin-top: 16rpx;
  border-top: 1rpx solid #eef2f6;
}

.advanced-toggle__text {
  color: #1b5faa;
  font-size: 26rpx;
}

.advanced-toggle__icon {
  color: #1b5faa;
  font-size: 22rpx;
}

.advanced-section {
  padding-top: 8rpx;
}
</style>
