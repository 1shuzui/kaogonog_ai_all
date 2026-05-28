<template>
  <div class="bank-editor page-container">
    <h2>{{ isEdit ? '编辑题目' : '新增题目' }}</h2>

    <a-form :model="form" layout="vertical" class="card" style="padding: 20px">
      <!-- 题干 -->
      <a-form-item label="题干" required>
        <a-textarea v-model:value="form.stem" :rows="4" placeholder="输入题目内容" />
      </a-form-item>

      <a-row :gutter="12">
        <a-col :span="12">
          <a-form-item label="题目分类">
            <a-select v-model:value="form.dimension" placeholder="选择题目分类">
              <a-select-option v-for="item in questionCategoryOptions" :key="item.key" :value="item.key">
                {{ item.name }}
              </a-select-option>
            </a-select>
          </a-form-item>
        </a-col>
        <a-col :span="12">
          <a-form-item label="省份">
            <a-select v-model:value="form.province" placeholder="选择省份">
              <a-select-option v-for="p in PROVINCES" :key="p.code" :value="p.code">
                {{ p.name }}
              </a-select-option>
            </a-select>
          </a-form-item>
        </a-col>
      </a-row>

      <a-alert
        v-if="form.categoryReviewStatus === 'needs_review'"
        type="warning"
        show-icon
        style="margin-bottom: 16px"
        :message="categoryReviewMessage"
      />

      <a-divider>考试分类与定向入口</a-divider>

      <a-row :gutter="12">
        <a-col :span="12">
          <a-form-item label="考试大类">
            <a-input v-model:value="form.examCategory" placeholder="如：省级公务员考试、事业单位考试" />
          </a-form-item>
        </a-col>
        <a-col :span="12">
          <a-form-item label="二级分类">
            <a-input v-model:value="form.examSubcategory" placeholder="如：安徽省、江苏省" />
          </a-form-item>
        </a-col>
      </a-row>

      <a-row :gutter="12">
        <a-col :span="8">
          <a-form-item label="系统">
            <a-input v-model:value="form.system" placeholder="如：监狱系统、税务系统" />
          </a-form-item>
        </a-col>
        <a-col :span="8">
          <a-form-item label="岗位类别">
            <a-input v-model:value="form.positionType" placeholder="如：乡镇岗、综合管理岗" />
          </a-form-item>
        </a-col>
        <a-col :span="8">
          <a-form-item label="岗位码">
            <a-input v-model:value="form.position" placeholder="如：township、prison" />
          </a-form-item>
        </a-col>
      </a-row>

      <a-form-item label="展示入口标签">
        <a-select v-model:value="form.portalTags" mode="tags" placeholder="如：医疗卫生面试、银行招考面试" />
      </a-form-item>

      <a-row :gutter="12">
        <a-col :span="12">
          <a-form-item label="准备时间(秒)">
            <a-input-number v-model:value="form.prepTime" :min="30" :max="300" style="width: 100%" />
          </a-form-item>
        </a-col>
        <a-col :span="12">
          <a-form-item label="作答时间(秒)">
            <a-input-number v-model:value="form.answerTime" :min="60" :max="600" style="width: 100%" />
          </a-form-item>
        </a-col>
      </a-row>

      <!-- 采分点 -->
      <a-form-item label="采分点">
        <div v-for="(point, index) in form.scoringPoints" :key="index" class="scoring-point">
          <a-input v-model:value="point.content" placeholder="采分点描述" style="flex: 1" />
          <a-input-number v-model:value="point.score" :min="1" :max="20" placeholder="分值" style="width: 80px" />
          <a-button type="text" danger @click="removePoint(index)">
            <DeleteOutlined />
          </a-button>
        </div>
        <a-button type="dashed" block @click="addPoint">
          <PlusOutlined /> 添加采分点
        </a-button>
      </a-form-item>

      <!-- 同义表述库 -->
      <a-form-item label="同义表述库">
        <a-select v-model:value="form.synonyms" mode="tags" placeholder="输入同义词后按回车" />
      </a-form-item>

      <!-- AI 关键词组 -->
      <a-divider>AI 关键词分组</a-divider>

      <a-form-item label="得分关键词">
        <a-select v-model:value="form.keywords.scoring" mode="tags" placeholder="输入关键词后按回车" />
      </a-form-item>

      <a-form-item label="扣分关键词">
        <a-select v-model:value="form.keywords.deducting" mode="tags" placeholder="输入关键词后按回车" />
      </a-form-item>

      <a-form-item label="加分关键词">
        <a-select v-model:value="form.keywords.bonus" mode="tags" placeholder="输入关键词后按回车" />
      </a-form-item>

      <!-- 操作 -->
      <div class="bank-editor__actions">
        <a-button @click="$router.back()">取消</a-button>
        <a-button type="primary" :loading="saving" @click="onSave">保存</a-button>
      </div>
    </a-form>
  </div>
</template>

<script setup>
import { computed, ref, reactive, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { PlusOutlined, DeleteOutlined } from '@ant-design/icons-vue'
import { useQuestionBankStore } from '@/stores/questionBank'
import { getQuestionById } from '@/api/questionBank'
import { PROVINCES } from '@/utils/constants'
import { message } from 'ant-design-vue'

const route = useRoute()
const router = useRouter()
const bankStore = useQuestionBankStore()

const isEdit = !!route.params.id
const saving = ref(false)
const questionCategoryOptions = [
  { key: 'analysis', name: '综合分析' },
  { key: 'practical', name: '组织管理' },
  { key: 'emergency', name: '应急应变' },
  { key: 'logic', name: '人际沟通' },
  { key: 'expression', name: '现场模拟' },
  { key: 'legal', name: '职业认知' }
]

const form = reactive({
  stem: '',
  dimension: undefined,
  province: 'national',
  prepTime: 90,
  answerTime: 180,
  categoryReviewStatus: 'confirmed',
  categoryConfidence: 0,
  categoryCandidates: [],
  categoryReviewReason: '',
  scoringPoints: [{ content: '', score: 5 }],
  synonyms: [],
  keywords: {
    scoring: [],
    deducting: [],
    bonus: []
  },
  examCategory: '',
  examSubcategory: '',
  system: '',
  positionType: '',
  position: '',
  portalTags: [],
  displayPortals: []
})

onMounted(async () => {
  if (isEdit) {
    const q = await getQuestionById(route.params.id)
    if (q) {
      Object.assign(form, {
        stem: q.stem,
        dimension: q.dimension,
        province: q.province,
        prepTime: q.prepTime,
        answerTime: q.answerTime,
        categoryReviewStatus: q.categoryReviewStatus || 'confirmed',
        categoryConfidence: q.categoryConfidence || 0,
        categoryCandidates: q.categoryCandidates || [],
        categoryReviewReason: q.categoryReviewReason || '',
        scoringPoints: q.scoringPoints?.length ? q.scoringPoints : [{ content: '', score: 5 }],
        synonyms: q.synonyms || [],
        keywords: {
          scoring: q.keywords?.scoring || [],
          deducting: q.keywords?.deducting || [],
          bonus: q.keywords?.bonus || []
        },
        examCategory: q.examCategory || '',
        examSubcategory: q.examSubcategory || '',
        system: q.system || '',
        positionType: q.positionType || '',
        position: q.position || '',
        portalTags: Array.isArray(q.portalTags) ? q.portalTags : [],
        displayPortals: Array.isArray(q.displayPortals) ? q.displayPortals : []
      })
    }
  } else {
    applyTargetDefaultsFromRoute()
  }
})

function applyTargetDefaultsFromRoute() {
  const query = route.query || {}
  const portalTag = String(query.portalTag || query.displayPortal || '').trim()
  Object.assign(form, {
    province: String(query.province === 'all' ? 'national' : query.province || form.province || 'national'),
    examCategory: String(query.examCategory || ''),
    examSubcategory: String(query.examSubcategory || ''),
    system: String(query.system || ''),
    positionType: String(query.positionType || ''),
    position: String(query.position || ''),
    portalTags: portalTag ? [portalTag] : [],
    displayPortals: portalTag ? [portalTag] : []
  })
}

function addPoint() {
  form.scoringPoints.push({ content: '', score: 5 })
}

function removePoint(index) {
  form.scoringPoints.splice(index, 1)
}

async function onSave() {
  if (!form.stem.trim()) {
    message.warning('请输入题干')
    return
  }
  saving.value = true
  try {
    const portalTags = Array.isArray(form.portalTags) ? form.portalTags.filter(Boolean) : []
    const payload = {
      ...form,
      portalTags,
      displayPortals: portalTags,
      categoryReviewStatus: 'confirmed'
    }
    if (isEdit) {
      await bankStore.editQuestion(route.params.id, payload)
    } else {
      await bankStore.addQuestion(payload)
    }
    message.success('保存成功')
    router.push('/bank')
  } catch (e) {
    message.error('保存失败')
  } finally {
    saving.value = false
  }
}

const categoryReviewMessage = computed(() => {
  const candidates = Array.isArray(form.categoryCandidates)
    ? form.categoryCandidates.map((item) => item.label || item.dimension).filter(Boolean).slice(0, 3)
    : []
  const suffix = candidates.length ? `候选分类：${candidates.join('、')}。` : ''
  return `${form.categoryReviewReason || '系统认为该题分类需要管理员确认。'}${suffix}保存后将标记为已确认。`
})
</script>

<style lang="less" scoped>
@import '@/styles/variables.less';

.bank-editor h2 {
  font-size: @font-size-xl;
  color: @text-primary;
  margin-bottom: 16px;
}

.scoring-point {
  display: flex;
  gap: 8px;
  align-items: center;
  margin-bottom: 8px;
}

.bank-editor__actions {
  display: flex;
  gap: 12px;
  justify-content: flex-end;
  margin-top: 16px;
}
</style>
