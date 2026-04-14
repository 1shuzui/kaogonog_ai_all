<template>
  <div class="bank-import page-container">
    <h2>批量导入题目</h2>

    <!-- 上传区域 -->
    <div class="card" style="padding: 20px">
      <a-upload-dragger
        :before-upload="handleFile"
        :show-upload-list="false"
        multiple
        accept=".xlsx,.xls,.json"
      >
        <p class="ant-upload-drag-icon">
          <InboxOutlined />
        </p>
        <p class="ant-upload-text">点击或拖拽文件到此处</p>
        <p class="ant-upload-hint">支持 .xlsx / .xls / .json 格式</p>
      </a-upload-dragger>

      <a-alert
        v-if="fileSummary"
        :message="`已选择: ${fileSummary}`"
        type="info"
        show-icon
        closable
        style="margin-top: 12px"
      />
    </div>

    <!-- 预览表格 -->
    <div class="card" style="margin-top: 12px; padding: 16px" v-if="previewData.length">
      <h4 style="margin-bottom: 12px">
        预览 (共 {{ previewData.length }} 道题目)
      </h4>
      <a-table
        :dataSource="previewData"
        :columns="columns"
        :pagination="{ pageSize: 5 }"
        size="small"
        :scroll="{ x: 600 }"
        rowKey="previewId"
      />

      <div style="margin-top: 16px; text-align: right">
        <a-button style="margin-right: 8px" @click="clearPreview">取消</a-button>
        <a-button type="primary" :loading="importing" @click="confirmImport">
          确认导入 {{ previewData.length }} 道题目
        </a-button>
      </div>
    </div>

    <!-- 字段说明 -->
    <div class="card" style="margin-top: 12px; padding: 16px">
      <h4>Excel 字段对照</h4>
      <a-table
        :dataSource="fieldDocs"
        :columns="[
          { title: '列名', dataIndex: 'name', width: 120 },
          { title: '说明', dataIndex: 'desc' },
          { title: '必填', dataIndex: 'required', width: 60 }
        ]"
        :pagination="false"
        size="small"
        rowKey="name"
      />
    </div>
  </div>
</template>

<script setup>
import { computed, ref } from 'vue'
import { useRouter } from 'vue-router'
import { InboxOutlined } from '@ant-design/icons-vue'
import { parseExcelFile, parseJsonFile } from '@/utils/excelParser'
import { useQuestionBankStore } from '@/stores/questionBank'
import { DIMENSIONS } from '@/utils/constants'
import { message } from 'ant-design-vue'

const router = useRouter()
const bankStore = useQuestionBankStore()

const fileNames = ref([])
const previewData = ref([])
const importing = ref(false)
const fileSummary = computed(() => {
  if (!fileNames.value.length) return ''
  if (fileNames.value.length <= 2) return fileNames.value.join('、')
  return `${fileNames.value[0]} 等 ${fileNames.value.length} 个文件`
})

const columns = [
  { title: '题干', dataIndex: 'stem', ellipsis: true, width: 300 },
  { title: '维度', dataIndex: 'dimension', width: 80,
    customRender: ({ text }) => {
      const d = DIMENSIONS.find(d => d.key === text)
      return d ? d.name : text
    }
  },
  { title: '采分点数', dataIndex: 'scoringPoints', width: 80,
    customRender: ({ text }) => (text?.length || 0) + ' 个'
  },
  { title: '省份', dataIndex: 'province', width: 80 },
  { title: '来源文档', dataIndex: 'sourceDocument', ellipsis: true, width: 180 }
]

const fieldDocs = [
  { name: '题干 / stem', desc: '题目内容', required: '是' },
  { name: '所属维度 / dimension', desc: '评分维度: legal/practical/logic/expression/analysis/emergency', required: '否' },
  { name: '省份 / province', desc: '省份代码，如 national/beijing/guangdong', required: '否' },
  { name: '准备时间 / prepTime', desc: '准备时间(秒)，默认90', required: '否' },
  { name: '作答时间 / answerTime', desc: '作答时间(秒)，默认180', required: '否' },
  { name: '采分点 / scoringPoints', desc: 'JSON数组: [{"content":"要点","score":5}]', required: '否' },
  { name: '来源文档 / sourceDocument', desc: '如真题所属文档名称，可用于前端区分来源', required: '否' },
  { name: '参考答案 / referenceAnswer', desc: '用于无模型时的保守规则评分', required: '否' },
  { name: '标签 / tags', desc: 'JSON数组或逗号分隔，保留岗位/地区等标签', required: '否' },
  { name: '同义表述库 / synonyms', desc: 'JSON数组或逗号分隔的词语', required: '否' },
  { name: '得分关键词 / scoringKeywords', desc: 'JSON数组或逗号分隔', required: '否' },
  { name: '扣分关键词 / deductingKeywords', desc: 'JSON数组或逗号分隔', required: '否' },
  { name: '加分关键词 / bonusKeywords', desc: 'JSON数组或逗号分隔', required: '否' }
]

async function handleFile(file) {
  try {
    let data
    if (file.name.endsWith('.json')) {
      data = await parseJsonFile(file)
    } else {
      data = await parseExcelFile(file)
    }
    const normalized = (data || []).map((item, index) => ({
      ...item,
      previewId: item.previewId || `preview_${Date.now()}_${Math.random().toString(36).slice(2, 8)}_${index}`
    }))
    previewData.value = [...previewData.value, ...normalized]
    if (!fileNames.value.includes(file.name)) {
      fileNames.value = [...fileNames.value, file.name]
    }
    if (data.length === 0) {
      message.warning(`${file.name} 未解析到有效题目`)
    } else {
      message.success(`${file.name} 解析成功: ${data.length} 道题目`)
    }
  } catch (e) {
    message.error(e.message || `${file.name} 文件解析失败`)
  }
  return false // 阻止自动上传
}

function clearPreview() {
  previewData.value = []
  fileNames.value = []
}

async function confirmImport() {
  if (!previewData.value.length) {
    message.warning('请先选择要导入的题目文件')
    return
  }
  importing.value = true
  try {
    const payload = previewData.value.map(({ previewId, ...item }) => item)
    const result = await bankStore.importFromFile(payload)
    message.success(`导入完成：成功 ${result?.imported || 0} 道，失败 ${result?.failed || 0} 道`)
    clearPreview()
    router.push('/bank')
  } catch (e) {
    message.error(e?.message || '导入失败')
  } finally {
    importing.value = false
  }
}
</script>

<style lang="less" scoped>
@import '@/styles/variables.less';

.bank-import h2 {
  font-size: @font-size-xl;
  color: @text-primary;
  margin-bottom: 16px;
}

h4 {
  font-size: @font-size-lg;
  color: @text-primary;
}
</style>
