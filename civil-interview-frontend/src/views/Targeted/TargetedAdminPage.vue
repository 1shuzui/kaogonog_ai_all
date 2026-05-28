<template>
  <div class="targeted-admin page-container">
    <div class="targeted-admin__header">
      <div>
        <h2>定向入口管理</h2>
        <p>维护定向备面的考试体系、地区来源和方向字段。普通用户只看到入口名称和真实分析结果。</p>
      </div>
      <a-button @click="$router.push('/targeted')">查看用户端</a-button>
    </div>

    <div class="targeted-admin__layout">
      <div class="card targeted-admin__picker">
        <h3>选择维护范围</h3>
        <p>先选考试大类，再选择地区来源和具体方向。</p>
        <div class="targeted-admin__row">
          <label>考试体系</label>
          <a-select
            v-model:value="selectedCategoryId"
            class="targeted-admin__select"
            @change="handleCategoryChange"
          >
            <a-select-option v-for="category in positionTree" :key="category.id" :value="category.id">
              {{ category.name }}
            </a-select-option>
          </a-select>
        </div>
        <div class="targeted-admin__row">
          <label>{{ regionLevelLabel }}</label>
          <a-select
            v-model:value="selectedRegionId"
            class="targeted-admin__select"
            :disabled="!currentRegions.length"
            @change="handleRegionChange"
          >
            <a-select-option v-for="region in currentRegions" :key="region.id" :value="region.id">
              {{ region.name }}
            </a-select-option>
          </a-select>
        </div>
        <div v-if="hasDirectionLevel" class="targeted-admin__row">
          <label>{{ directionLevelLabel }}</label>
          <a-select
            v-model:value="selectedTargetCode"
            class="targeted-admin__select"
            :disabled="!currentDirections.length"
            @change="handleDirectionChange"
          >
            <a-select-option v-for="direction in currentDirections" :key="direction.id" :value="direction.id">
              {{ direction.name }}
            </a-select-option>
          </a-select>
        </div>
      </div>

      <div class="card targeted-admin__detail">
        <template v-if="selectedTarget">
          <h3>{{ selectedTarget.targetName }}</h3>
          <div class="targeted-admin__tags">
            <a-tag v-if="selectedTarget.examCategory" color="blue">{{ selectedTarget.examCategory }}</a-tag>
            <a-tag v-if="selectedTarget.examSubcategory" color="cyan">{{ selectedTarget.examSubcategory }}</a-tag>
            <a-tag v-if="selectedTarget.system" color="purple">{{ selectedTarget.system }}</a-tag>
            <a-tag v-if="selectedTarget.positionType" color="orange">{{ selectedTarget.positionType }}</a-tag>
            <a-tag v-if="selectedTarget.portalTag" color="gold">{{ selectedTarget.portalTag }}</a-tag>
            <a-tag v-if="selectedTarget.interviewFormat" color="green">{{ selectedTarget.interviewFormat }}</a-tag>
            <a-tag v-if="selectedTarget.timingMode" color="lime">{{ selectedTarget.timingMode }}</a-tag>
          </div>

          <a-alert
            v-if="maintenanceHint"
            type="info"
            show-icon
            class="targeted-admin__alert"
            :message="maintenanceHint"
          />

          <a-descriptions bordered size="small" :column="1">
            <a-descriptions-item label="入口编码">{{ selectedTarget.targetCode }}</a-descriptions-item>
            <a-descriptions-item label="省份">{{ selectedTarget.province || 'all' }}</a-descriptions-item>
            <a-descriptions-item label="岗位码">{{ selectedTarget.position || '整类入口' }}</a-descriptions-item>
            <a-descriptions-item label="考试大类">{{ selectedTarget.examCategory || '-' }}</a-descriptions-item>
            <a-descriptions-item label="二级分类">{{ selectedTarget.examSubcategory || '-' }}</a-descriptions-item>
            <a-descriptions-item label="题量">{{ selectedTarget.questionCount ? `${selectedTarget.questionCount}题` : '-' }}</a-descriptions-item>
            <a-descriptions-item label="计时模式">{{ selectedTarget.timingMode || selectedTarget.interviewFormat || '-' }}</a-descriptions-item>
            <a-descriptions-item label="题型范围">{{ selectedTarget.questionTypeScope || '-' }}</a-descriptions-item>
          </a-descriptions>

          <div class="targeted-admin__actions">
            <a-button @click="openQuestionList">
              <EditOutlined /> 修改已有题目
            </a-button>
            <a-button type="primary" @click="createQuestionForTarget">
              <PlusOutlined /> 新增匹配题目
            </a-button>
            <a-button @click="openImport">
              <UploadOutlined /> 批量导入上传
            </a-button>
          </div>

          <div class="targeted-admin__secondary-actions">
            <a-button @click="copyPayload">复制入口字段</a-button>
          </div>

          <div class="targeted-admin__focus-editor">
            <div class="targeted-admin__section-title">
              <div>
                <h4>重点分析发布内容</h4>
                <p>保存后，用户端优先展示这里发布的内容；停用后恢复题库自动统计。</p>
              </div>
              <a-tag :color="focusConfig?.enabled ? 'green' : 'default'">
                {{ focusConfig?.enabled ? '已发布' : '自动统计' }}
              </a-tag>
            </div>

            <a-spin :spinning="focusLoading">
              <a-alert
                v-if="focusEditor.isFallback"
                class="targeted-admin__alert"
                type="warning"
                show-icon
                message="当前入口暂无足够题库数据，可先补充题库，或发布管理员维护内容。"
              />

              <div class="targeted-admin__field">
                <label>匹配题量</label>
                <a-input-number v-model:value="focusEditor.questionCount" :min="0" :max="100000" />
              </div>

              <div class="targeted-admin__editor-block">
                <div class="targeted-admin__block-head">
                  <strong>核心能力与权重</strong>
                  <a-button size="small" @click="addCoreFocus">添加能力</a-button>
                </div>
                <div
                  v-for="(item, index) in focusEditor.coreFocus"
                  :key="`core-${index}`"
                  class="targeted-admin__editor-row"
                >
                  <a-input v-model:value="item.name" placeholder="能力名称" />
                  <a-input-number v-model:value="item.weight" :min="0" :max="100" addon-after="%" />
                  <a-textarea v-model:value="item.desc" placeholder="分析说明" :auto-size="{ minRows: 1, maxRows: 3 }" />
                  <a-button danger @click="removeCoreFocus(index)">删除</a-button>
                </div>
              </div>

              <div class="targeted-admin__editor-block">
                <div class="targeted-admin__block-head">
                  <strong>高频题型</strong>
                  <a-button size="small" @click="addHighFreqType">添加题型</a-button>
                </div>
                <div
                  v-for="(item, index) in focusEditor.highFreqTypes"
                  :key="`type-${index}`"
                  class="targeted-admin__editor-row targeted-admin__editor-row--types"
                >
                  <a-input v-model:value="item.type" placeholder="题型名称" />
                  <a-select v-model:value="item.frequency">
                    <a-select-option value="高">高</a-select-option>
                    <a-select-option value="中">中</a-select-option>
                    <a-select-option value="低">低</a-select-option>
                  </a-select>
                  <a-input-number v-model:value="item.questionCount" :min="0" :max="100000" placeholder="题量" />
                  <a-textarea v-model:value="item.example" placeholder="示例或说明" :auto-size="{ minRows: 1, maxRows: 3 }" />
                  <a-button danger @click="removeHighFreqType(index)">删除</a-button>
                </div>
              </div>

              <div class="targeted-admin__field">
                <label>热门话题</label>
                <a-textarea v-model:value="hotTopicsText" placeholder="一行一个话题" :auto-size="{ minRows: 3, maxRows: 8 }" />
              </div>

              <div class="targeted-admin__field">
                <label>备考策略</label>
                <a-textarea v-model:value="strategyText" placeholder="一行一条策略" :auto-size="{ minRows: 4, maxRows: 10 }" />
              </div>

              <div class="targeted-admin__focus-actions">
                <a-button @click="loadFocusEditor(true)">
                  <ReloadOutlined /> 载入自动统计
                </a-button>
                <a-button type="primary" :loading="focusSaving" @click="saveFocusEditor">
                  <SaveOutlined /> 保存并发布
                </a-button>
                <a-button danger :disabled="!focusConfig" @click="disableFocusEditor">
                  <StopOutlined /> 停用发布
                </a-button>
              </div>
            </a-spin>
          </div>
        </template>
        <EmptyState v-else text="请选择一个定向入口" />
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed, onMounted, ref, watch } from 'vue'
import { message } from 'ant-design-vue'
import { EditOutlined, PlusOutlined, ReloadOutlined, SaveOutlined, StopOutlined, UploadOutlined } from '@ant-design/icons-vue'
import { useRouter } from 'vue-router'
import EmptyState from '@/components/common/EmptyState.vue'
import { disableFocusAdminConfig, getFocusAdminConfig, saveFocusAdminConfig } from '@/api/targeted'
import { useTargetedStore } from '@/stores/targeted'
import { getTargetMaintenanceHint, mergeTargetPayload } from '@/utils/targetedOptions'

const router = useRouter()
const targetedStore = useTargetedStore()
const selectedCategoryId = ref('')
const selectedRegionId = ref('')
const selectedTargetCode = ref('')
const positionTree = computed(() => targetedStore.positionTree || [])
const selectedCategory = computed(() => positionTree.value.find((item) => item.id === selectedCategoryId.value) || positionTree.value[0] || null)
const levelLabels = computed(() => selectedCategory.value?.levelLabels || {})
const regionLevelLabel = computed(() => levelLabels.value.region || '地区 / 来源')
const directionLevelLabel = computed(() => levelLabels.value.direction || '方向')
const currentRegions = computed(() => selectedCategory.value?.children || [])
const selectedRegion = computed(() => currentRegions.value.find((item) => item.id === selectedRegionId.value) || currentRegions.value[0] || null)
const currentDirections = computed(() => selectedRegion.value?.directions || [])
const hasDirectionLevel = computed(() => currentDirections.value.length > 0)
const selectedDirection = computed(() => currentDirections.value.find((item) => item.id === selectedTargetCode.value) || currentDirections.value[0] || null)
const selectedTarget = computed(() => (
  selectedCategory.value && selectedRegion.value && (!hasDirectionLevel.value || selectedDirection.value)
    ? mergeTargetPayload(selectedCategory.value, selectedRegion.value, selectedDirection.value || {})
    : null
))
const maintenanceHint = computed(() => getTargetMaintenanceHint(selectedRegion.value || selectedTarget.value || {}))
const focusLoading = ref(false)
const focusSaving = ref(false)
const focusConfig = ref(null)
const focusEditor = ref(createBlankFocusEditor())
const hotTopicsText = ref('')
const strategyText = ref('')

onMounted(async () => {
  await targetedStore.fetchPositionTree()
  selectFirst()
})

watch(
  () => selectedTarget.value?.targetCode,
  (targetCode) => {
    if (targetCode) loadFocusEditor()
  }
)

function createBlankFocusEditor() {
  return {
    coreFocus: [],
    highFreqTypes: [],
    hotTopics: [],
    strategy: [],
    questionCount: 0,
    isFallback: false
  }
}

function normalizeList(value) {
  if (Array.isArray(value)) return value.map((item) => String(item || '').trim()).filter(Boolean)
  if (typeof value === 'string') return value.split(/\n|,|，/).map((item) => item.trim()).filter(Boolean)
  return []
}

function applyFocusPayload(payload = {}) {
  focusEditor.value = {
    coreFocus: Array.isArray(payload.coreFocus)
      ? payload.coreFocus.map((item) => ({
          name: item?.name || '',
          weight: Number(item?.weight || 0),
          desc: item?.desc || '',
          questionCount: Number(item?.questionCount || 0)
        }))
      : [],
    highFreqTypes: Array.isArray(payload.highFreqTypes)
      ? payload.highFreqTypes.map((item) => ({
          type: item?.type || '',
          frequency: item?.frequency || '中',
          example: item?.example || '',
          questionCount: Number(item?.questionCount || 0)
        }))
      : [],
    hotTopics: normalizeList(payload.hotTopics),
    strategy: normalizeList(payload.strategy),
    questionCount: Number(payload.questionCount || 0),
    isFallback: !!payload.isFallback
  }
  hotTopicsText.value = focusEditor.value.hotTopics.join('\n')
  strategyText.value = focusEditor.value.strategy.join('\n')
}

async function loadFocusEditor(forceAuto = false) {
  if (!selectedTarget.value?.targetCode) return
  focusLoading.value = true
  try {
    const response = await getFocusAdminConfig(queryFromTarget())
    focusConfig.value = response?.config || null
    applyFocusPayload(forceAuto ? response?.auto : response?.current || response?.auto)
    if (forceAuto) {
      message.success('已载入题库自动统计结果')
    }
  } finally {
    focusLoading.value = false
  }
}

function addCoreFocus() {
  focusEditor.value.coreFocus.push({ name: '', weight: 20, desc: '', questionCount: 0 })
}

function removeCoreFocus(index) {
  focusEditor.value.coreFocus.splice(index, 1)
}

function addHighFreqType() {
  focusEditor.value.highFreqTypes.push({ type: '', frequency: '中', example: '', questionCount: 0 })
}

function removeHighFreqType(index) {
  focusEditor.value.highFreqTypes.splice(index, 1)
}

function buildFocusPayload() {
  return {
    ...focusEditor.value,
    hotTopics: normalizeList(hotTopicsText.value),
    strategy: normalizeList(strategyText.value)
  }
}

async function saveFocusEditor() {
  if (!selectedTarget.value?.targetCode) return
  focusSaving.value = true
  try {
    const response = await saveFocusAdminConfig({
      target: queryFromTarget(),
      payload: buildFocusPayload(),
      enabled: true
    })
    focusConfig.value = response?.config || null
    applyFocusPayload(response?.current || response?.config?.payload || buildFocusPayload())
    message.success('重点分析已发布')
  } finally {
    focusSaving.value = false
  }
}

async function disableFocusEditor() {
  if (!selectedTarget.value?.targetCode) return
  await disableFocusAdminConfig({ target: queryFromTarget() })
  focusConfig.value = null
  await loadFocusEditor(true)
  message.success('已停用发布内容，恢复自动统计')
}

function selectFirst() {
  selectCategory(positionTree.value[0])
}

function applySelection(category, region, direction) {
  if (!category || !region) return
  selectedCategoryId.value = category.id
  selectedRegionId.value = region.id
  selectedTargetCode.value = direction?.id || direction?.code || ''
}

function selectCategory(category) {
  const region = category?.children?.[0]
  const direction = region?.directions?.[0]
  applySelection(category, region, direction || null)
}

function selectRegion(region) {
  const direction = region?.directions?.[0]
  applySelection(selectedCategory.value, region, direction || null)
}

function selectDirection(direction) {
  if (!direction) return
  selectedTargetCode.value = direction.id || direction.code
}

function handleCategoryChange(categoryId) {
  selectCategory(positionTree.value.find((item) => item.id === categoryId))
}

function handleRegionChange(regionId) {
  selectRegion(currentRegions.value.find((item) => item.id === regionId))
}

function handleDirectionChange(directionId) {
  selectDirection(currentDirections.value.find((item) => item.id === directionId))
}

function queryFromTarget() {
  const query = Object.fromEntries(
    Object.entries(selectedTarget.value || {})
      .filter(([, value]) => value !== undefined && value !== null && String(value).trim() !== '')
  )
  if (query.province === 'all') query.province = 'national'
  return query
}

function createQuestionForTarget() {
  router.push({ path: '/bank/edit', query: queryFromTarget() })
}

function openQuestionList() {
  router.push({ path: '/bank', query: queryFromTarget() })
}

function openImport() {
  router.push({ path: '/bank/import', query: queryFromTarget() })
}

async function copyPayload() {
  const text = JSON.stringify(queryFromTarget(), null, 2)
  try {
    await navigator.clipboard.writeText(text)
    message.success('入口字段已复制')
  } catch {
    message.info(text)
  }
}
</script>

<style lang="less" scoped>
@import '@/styles/variables.less';

.targeted-admin__header {
  display: flex;
  justify-content: space-between;
  gap: 16px;
  margin-bottom: 16px;

  h2 {
    margin: 0 0 4px;
    color: @text-primary;
    font-size: @font-size-xl;
  }

  p {
    margin: 0;
    color: @text-secondary;
    font-size: @font-size-sm;
  }
}

.targeted-admin__layout {
  display: grid;
  grid-template-columns: minmax(0, 1.1fr) minmax(360px, 0.9fr);
  gap: 16px;
  align-items: start;
}

.targeted-admin__tree,
.targeted-admin__picker,
.targeted-admin__detail {
  padding: 16px;
}

.targeted-admin__picker {
  h3 {
    margin: 0 0 4px;
    color: @text-primary;
    font-size: @font-size-base;
  }

  p {
    margin: 0 0 10px;
    color: @text-secondary;
    font-size: @font-size-xs;
  }
}

.targeted-admin__row {
  display: grid;
  grid-template-columns: 104px minmax(0, 1fr);
  gap: 12px;
  align-items: center;
  margin-top: 12px;

  label {
    color: @text-secondary;
    font-size: @font-size-sm;
    font-weight: 600;
  }
}

.targeted-admin__select {
  width: 100%;
}

.targeted-admin__tags {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  margin-bottom: 12px;
}

.targeted-admin__alert {
  margin-bottom: 12px;
}

.targeted-admin__actions {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(136px, 1fr));
  gap: 10px;
  margin-top: 16px;

  :deep(.ant-btn) {
    width: 100%;
    min-width: 0;
    height: auto;
    min-height: 36px;
    padding: 7px 10px;
    white-space: normal;
    line-height: 1.35;
  }
}

.targeted-admin__secondary-actions {
  margin-top: 10px;

  :deep(.ant-btn) {
    width: 100%;
    min-width: 0;
    white-space: normal;
  }
}

.targeted-admin__focus-editor {
  margin-top: 18px;
  padding-top: 16px;
  border-top: 1px solid @border-color;
}

.targeted-admin__section-title,
.targeted-admin__block-head,
.targeted-admin__focus-actions {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 10px;
}

.targeted-admin__section-title {
  margin-bottom: 12px;

  h4 {
    margin: 0 0 4px;
    color: @text-primary;
    font-size: @font-size-base;
  }

  p {
    margin: 0;
    color: @text-secondary;
    font-size: @font-size-xs;
  }
}

.targeted-admin__field {
  display: grid;
  grid-template-columns: 96px minmax(0, 1fr);
  gap: 10px;
  align-items: start;
  margin-top: 12px;

  label {
    padding-top: 5px;
    color: @text-secondary;
    font-size: @font-size-sm;
    font-weight: 600;
  }
}

.targeted-admin__editor-block {
  margin-top: 14px;
}

.targeted-admin__block-head {
  margin-bottom: 8px;

  strong {
    color: @text-primary;
    font-size: @font-size-sm;
  }
}

.targeted-admin__editor-row {
  display: grid;
  grid-template-columns: minmax(100px, 0.8fr) 118px minmax(160px, 1.4fr) 72px;
  gap: 8px;
  align-items: start;
  margin-bottom: 8px;

  :deep(.ant-btn) {
    min-width: 0;
    padding-inline: 10px;
  }
}

.targeted-admin__editor-row--types {
  grid-template-columns: minmax(100px, 0.7fr) 82px 96px minmax(160px, 1.2fr) 72px;
}

.targeted-admin__focus-actions {
  justify-content: flex-end;
  flex-wrap: wrap;
  margin-top: 14px;

  :deep(.ant-btn) {
    min-width: 118px;
  }
}

@media (max-width: 900px) {
  .targeted-admin__header {
    flex-direction: column;
    align-items: stretch;
  }

  .targeted-admin__actions {
    grid-template-columns: 1fr;
  }

  .targeted-admin__layout {
    grid-template-columns: 1fr;
  }

  .targeted-admin__row {
    grid-template-columns: 1fr;
    gap: 6px;
  }

  .targeted-admin__field,
  .targeted-admin__editor-row,
  .targeted-admin__editor-row--types {
    grid-template-columns: 1fr;
  }

  .targeted-admin__section-title,
  .targeted-admin__block-head,
  .targeted-admin__focus-actions {
    align-items: stretch;
    flex-direction: column;
  }
}
</style>
