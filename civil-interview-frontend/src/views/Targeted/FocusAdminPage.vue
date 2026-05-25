<template>
  <div class="focus-admin page-container">
    <div class="focus-admin__header">
      <a-button type="text" @click="$router.back()">
        <LeftOutlined /> 返回
      </a-button>
      <div>
        <h2>定向备面重点维护</h2>
        <p>基于真实题库生成分析结果，管理员可编辑后发布给普通用户。</p>
      </div>
    </div>

    <div class="card focus-admin__filters">
      <a-space wrap>
        <a-select v-model:value="province" style="width: 180px" placeholder="省份">
          <a-select-option v-for="item in PROVINCES" :key="item.code" :value="item.code">
            {{ item.name }}
          </a-select-option>
        </a-select>
        <a-select v-model:value="position" style="width: 220px" placeholder="岗位系统">
          <a-select-option v-for="item in positionOptions" :key="item.code" :value="item.code">
            {{ item.name }}
          </a-select-option>
        </a-select>
        <a-button type="primary" :loading="loading" @click="loadConfig">加载配置</a-button>
        <a-button :loading="analyzing" @click="runAnalyze">重新分析题库</a-button>
      </a-space>
    </div>

    <a-spin :spinning="loading">
      <template v-if="config">
        <div class="focus-admin__grid">
          <div class="card focus-admin__panel">
            <div class="focus-admin__panel-head">
              <h3>自动分析结果</h3>
              <a-tag>{{ autoResult.questionCount || 0 }} 道题</a-tag>
            </div>
            <a-alert
              v-if="!hasAutoContent"
              type="warning"
              show-icon
              message="当前方向暂无足够题库数据"
              style="margin-bottom: 12px"
            />
            <FocusPreview :data="autoResult" />
            <a-button block style="margin-top: 12px" @click="useAutoResult">使用自动分析结果</a-button>
          </div>

          <div class="card focus-admin__panel">
            <div class="focus-admin__panel-head">
              <h3>发布内容</h3>
              <a-switch v-model:checked="form.isActive" checked-children="启用" un-checked-children="停用" />
            </div>
            <a-radio-group v-model:value="form.publishMode" button-style="solid" style="margin-bottom: 12px">
              <a-radio-button value="auto">使用自动结果</a-radio-button>
              <a-radio-button value="manual">使用编辑结果</a-radio-button>
            </a-radio-group>

            <a-divider orientation="left">核心能力</a-divider>
            <div v-for="(item, index) in form.publishedResult.coreFocus" :key="`core-${index}`" class="focus-admin__row">
              <a-input v-model:value="item.name" placeholder="能力名称" />
              <a-input-number v-model:value="item.weight" :min="0" :max="100" />
              <a-input v-model:value="item.desc" placeholder="说明" />
              <a-button type="text" danger @click="removeItem('coreFocus', index)">删除</a-button>
            </div>
            <a-button block type="dashed" @click="addCoreFocus">添加核心能力</a-button>

            <a-divider orientation="left">高频题型</a-divider>
            <div v-for="(item, index) in form.publishedResult.highFreqTypes" :key="`freq-${index}`" class="focus-admin__row">
              <a-input v-model:value="item.type" placeholder="题型" />
              <a-select v-model:value="item.frequency" style="width: 90px">
                <a-select-option value="高">高</a-select-option>
                <a-select-option value="中">中</a-select-option>
                <a-select-option value="低">低</a-select-option>
              </a-select>
              <a-input v-model:value="item.example" placeholder="说明或例题" />
              <a-button type="text" danger @click="removeItem('highFreqTypes', index)">删除</a-button>
            </div>
            <a-button block type="dashed" @click="addHighFreqType">添加高频题型</a-button>

            <a-divider orientation="left">热门话题</a-divider>
            <a-select v-model:value="form.publishedResult.hotTopics" mode="tags" placeholder="输入后回车" />

            <a-divider orientation="left">备考策略</a-divider>
            <div v-for="(item, index) in form.publishedResult.strategy" :key="`strategy-${index}`" class="focus-admin__strategy-row">
              <a-textarea v-model:value="form.publishedResult.strategy[index]" :rows="2" />
              <a-button type="text" danger @click="removeItem('strategy', index)">删除</a-button>
            </div>
            <a-button block type="dashed" @click="addStrategy">添加策略</a-button>

            <div class="focus-admin__actions">
              <a-button danger :disabled="!config?.id" @click="disableConfig">停用</a-button>
              <a-button type="primary" :loading="saving" @click="saveConfig">保存发布</a-button>
            </div>
          </div>
        </div>
      </template>
      <EmptyState v-else text="请选择省份和岗位后加载配置" />
    </a-spin>
  </div>
</template>

<script setup>
import { computed, reactive, ref } from 'vue'
import { LeftOutlined } from '@ant-design/icons-vue'
import { message } from 'ant-design-vue'
import EmptyState from '@/components/common/EmptyState.vue'
import { analyzeFocusAdmin, disableFocusAdmin, getFocusAdmin, updateFocusAdmin } from '@/api/targeted'
import { PROVINCES, POSITION_SYSTEMS } from '@/utils/constants'
import { JIANGSU_TARGETED_POSITIONS } from '@/utils/jiangsuJobs'

const province = ref('jiangsu')
const position = ref('general')
const loading = ref(false)
const analyzing = ref(false)
const saving = ref(false)
const config = ref(null)
const form = reactive({
  publishMode: 'auto',
  isActive: true,
  publishedResult: emptyResult()
})

const positionOptions = computed(() => [...POSITION_SYSTEMS, ...JIANGSU_TARGETED_POSITIONS])
const autoResult = computed(() => config.value?.autoResult || emptyResult())
const hasAutoContent = computed(() => (
  Array.isArray(autoResult.value.coreFocus) && autoResult.value.coreFocus.length
))

function emptyResult() {
  return {
    coreFocus: [],
    highFreqTypes: [],
    hotTopics: [],
    strategy: [],
    questionCount: 0
  }
}

function cloneResult(value = {}) {
  return JSON.parse(JSON.stringify({
    ...emptyResult(),
    ...value,
    coreFocus: Array.isArray(value.coreFocus) ? value.coreFocus : [],
    highFreqTypes: Array.isArray(value.highFreqTypes) ? value.highFreqTypes : [],
    hotTopics: Array.isArray(value.hotTopics) ? value.hotTopics : [],
    strategy: Array.isArray(value.strategy) ? value.strategy : []
  }))
}

function applyConfig(value) {
  config.value = value
  form.publishMode = value?.publishMode || 'auto'
  form.isActive = value?.isActive !== false
  form.publishedResult = cloneResult(value?.publishedResult?.coreFocus?.length ? value.publishedResult : value?.autoResult)
}

async function loadConfig() {
  loading.value = true
  try {
    const result = await getFocusAdmin({ province: province.value, position: position.value })
    applyConfig(result)
  } finally {
    loading.value = false
  }
}

async function runAnalyze() {
  analyzing.value = true
  try {
    const result = await analyzeFocusAdmin({ province: province.value, position: position.value })
    applyConfig(result)
    message.success('已根据题库重新分析')
  } finally {
    analyzing.value = false
  }
}

function useAutoResult() {
  form.publishMode = 'auto'
  form.publishedResult = cloneResult(autoResult.value)
}

function addCoreFocus() {
  form.publishedResult.coreFocus.push({ name: '', weight: 20, desc: '' })
}

function addHighFreqType() {
  form.publishedResult.highFreqTypes.push({ type: '', frequency: '中', example: '' })
}

function addStrategy() {
  form.publishedResult.strategy.push('')
}

function removeItem(key, index) {
  form.publishedResult[key].splice(index, 1)
}

async function saveConfig() {
  if (!config.value?.id) return
  saving.value = true
  try {
    const result = await updateFocusAdmin(config.value.id, {
      province: province.value,
      position: position.value,
      publishMode: form.publishMode,
      isActive: form.isActive,
      publishedResult: form.publishedResult
    })
    applyConfig(result)
    message.success('重点分析已保存')
  } finally {
    saving.value = false
  }
}

async function disableConfig() {
  if (!config.value?.id) return
  const result = await disableFocusAdmin(config.value.id)
  applyConfig(result)
  message.success('已停用该方向配置')
}
</script>

<script>
export default {
  components: {
    FocusPreview: {
      props: { data: { type: Object, default: () => ({}) } },
      template: `
        <div class="focus-preview">
          <p v-if="data.message" class="focus-preview__message">{{ data.message }}</p>
          <div v-for="item in data.coreFocus || []" :key="item.name" class="focus-preview__item">
            <strong>{{ item.name }} · {{ item.weight }}%</strong>
            <span>{{ item.desc }}</span>
          </div>
          <div v-if="data.hotTopics?.length" class="focus-preview__topics">
            <span v-for="topic in data.hotTopics" :key="topic">{{ topic }}</span>
          </div>
        </div>
      `
    }
  }
}
</script>

<style lang="less" scoped>
@import '@/styles/variables.less';

.focus-admin__header {
  display: flex;
  align-items: flex-start;
  gap: 8px;
  margin-bottom: 16px;

  h2 {
    margin: 0;
    color: @text-primary;
  }

  p {
    margin: 4px 0 0;
    color: @text-secondary;
  }
}

.focus-admin__filters {
  padding: 16px;
  margin-bottom: 16px;
}

.focus-admin__grid {
  display: grid;
  grid-template-columns: minmax(280px, 0.85fr) minmax(420px, 1.15fr);
  gap: 16px;
}

.focus-admin__panel {
  padding: 16px;
}

.focus-admin__panel-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 12px;

  h3 {
    margin: 0;
  }
}

.focus-admin__row,
.focus-admin__strategy-row {
  display: grid;
  grid-template-columns: 150px 90px minmax(180px, 1fr) 64px;
  gap: 8px;
  margin-bottom: 8px;
  align-items: center;
}

.focus-admin__strategy-row {
  grid-template-columns: minmax(240px, 1fr) 64px;
}

.focus-admin__actions {
  display: flex;
  justify-content: flex-end;
  gap: 12px;
  margin-top: 18px;
}

.focus-preview__item {
  display: flex;
  flex-direction: column;
  gap: 4px;
  padding: 10px 0;
  border-bottom: 1px solid @divider-color;
}

.focus-preview__item span,
.focus-preview__message {
  color: @text-secondary;
}

.focus-preview__topics {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
  margin-top: 12px;

  span {
    padding: 3px 8px;
    border-radius: 12px;
    background: @bg-light-blue;
    color: @primary-color;
    font-size: 12px;
  }
}

@media (max-width: 900px) {
  .focus-admin__grid {
    grid-template-columns: 1fr;
  }
}
</style>
