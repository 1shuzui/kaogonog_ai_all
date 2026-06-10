<!--
题库导入页，给管理员批量上传模板和校验结果，避免原始文档字段直接污染线上题库。

导入只是管理员维护入口之一，真实分类纠偏仍以后端导入脚本和题库元数据校验为准；页面不把文件名关键词直接当最终分类。

@param: 无；上传文件来自管理员选择，导入结果来自 questionBank API。
@return: 渲染上传区域、导入进度、校验结果和错误提示。
@raises: 不主动抛业务异常；非管理员、模板错误或上传失败由页面提示承接。
-->
<template>
  <div class="bank-import page-container">
    <h2>批量导入题目</h2>

    <!-- 上传区域 -->
    <div class="card" style="padding: 20px">
      <a-upload-dragger
        :before-upload="handleFile"
        :show-upload-list="false"
        accept=".xlsx,.json"
      >
        <p class="ant-upload-drag-icon">
          <InboxOutlined />
        </p>
        <p class="ant-upload-text">点击或拖拽文件到此处</p>
        <p class="ant-upload-hint">支持 .xlsx / .json 格式</p>
      </a-upload-dragger>

      <a-alert
        v-if="fileName"
        :message="`已选择: ${fileName}`"
        type="info"
        show-icon
        closable
        style="margin-top: 12px"
      />
    </div>

    <!-- 预览表格 -->
    <div class="card" style="margin-top: 12px; padding: 16px" v-if="selectedFile">
      <h4 style="margin-bottom: 12px">
        {{ previewData.length ? `预览 (共 ${previewData.length} 道题目)` : 'Excel 将上传到服务器端解析' }}
      </h4>
      <a-table
        v-if="previewData.length"
        :dataSource="previewData"
        :columns="columns"
        :pagination="{ pageSize: 5 }"
        size="small"
        :scroll="{ x: 600 }"
        rowKey="id"
      />

      <div style="margin-top: 16px; text-align: right">
        <a-button style="margin-right: 8px" @click="clearPreview">取消</a-button>
        <a-button type="primary" :loading="importing" @click="confirmImport">
          {{ previewData.length ? `确认导入 ${previewData.length} 道题目` : '上传并导入 Excel' }}
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
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import { InboxOutlined } from '@ant-design/icons-vue'
import { parseJsonFile } from '@/utils/excelParser'
import { useQuestionBankStore } from '@/stores/questionBank'
import { DIMENSIONS } from '@/utils/constants'
import { message } from 'ant-design-vue'

const router = useRouter()
const bankStore = useQuestionBankStore()

const fileName = ref('')
const selectedFile = ref(null)
const previewData = ref([])
const importing = ref(false)

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
  { title: '省份', dataIndex: 'province', width: 80 }
]

const fieldDocs = [
  { name: '题干 / stem', desc: '题目内容', required: '是' },
  { name: '所属维度 / dimension', desc: '评分维度: legal/practical/logic/expression/analysis/emergency', required: '否' },
  { name: '省份 / province', desc: '省份代码，如 national/beijing/guangdong', required: '否' },
  { name: '准备时间 / prepTime', desc: '准备时间(秒)，默认90', required: '否' },
  { name: '作答时间 / answerTime', desc: '作答时间(秒)，默认180', required: '否' },
  { name: '采分点 / scoringPoints', desc: 'JSON数组: [{"content":"要点","score":5}]', required: '否' },
  { name: '同义表述库 / synonyms', desc: 'JSON数组或逗号分隔的词语', required: '否' },
  { name: '得分关键词 / scoringKeywords', desc: 'JSON数组或逗号分隔', required: '否' },
  { name: '扣分关键词 / deductingKeywords', desc: 'JSON数组或逗号分隔', required: '否' },
  { name: '加分关键词 / bonusKeywords', desc: 'JSON数组或逗号分隔', required: '否' }
]

async function handleFile(file) {
  fileName.value = file.name
  selectedFile.value = file
  try {
    let data
    const lowerName = file.name.toLowerCase()
    if (lowerName.endsWith('.json')) {
      data = await parseJsonFile(file)
      previewData.value = data
      if (data.length === 0) {
        message.warning('未解析到有效题目')
      } else {
        message.success(`解析成功: ${data.length} 道题目`)
      }
    } else if (lowerName.endsWith('.xlsx')) {
      previewData.value = []
      message.info('已选择 Excel 文件，确认后将上传服务器解析导入')
    } else {
      throw new Error('仅支持 .xlsx / .json 格式')
    }
  } catch (e) {
    message.error(e.message || '文件解析失败')
  }
  return false // 阻止自动上传
}

function clearPreview() {
  previewData.value = []
  fileName.value = ''
  selectedFile.value = null
}

async function confirmImport() {
  if (!selectedFile.value) {
    message.warning('请先选择文件')
    return
  }
  importing.value = true
  try {
    const result = await bankStore.importFromFile(selectedFile.value)
    const imported = Number(result?.imported ?? 0)
    const failed = Number(result?.failed ?? 0)
    message.success(`导入完成：成功 ${imported} 道，失败 ${failed} 道`)
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
