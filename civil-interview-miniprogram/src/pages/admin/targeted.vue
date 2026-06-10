<!--
小程序定向入口管理页复用用户端动态层级，方便管理员核对考试体系、地区来源和方向是否按真实考试树展示。
管理员可查看自动分析与发布状态，但普通用户仍只能看到已确认内容；无题库方向不能显示“等待上传”等内部文案。

@param: 无；页面读取 targeted store、管理员身份和当前层级选择。
@return: 渲染动态层级选择、入口元数据、自动分析和发布维护操作。
@raises: 不主动抛业务异常；接口失败、未登录和权限不足由请求层或页面提示承接。
-->
<template>
  <view class="page">
    <view class="admin-header">
      <view>
        <text class="page-title">定向入口管理</text>
        <text class="page-desc">维护定向备面的考试体系、地区来源和方向字段。普通用户只看到入口名称和真实分析结果。</text>
      </view>
    </view>

    <view v-if="!userStore.isAdmin" class="card">
      <EmptyState title="无管理员权限" desc="请使用管理员账号登录后再访问。" />
    </view>

    <template v-else>
      <view class="card picker-card">
        <view class="section-head">
          <text class="section-title">选择维护范围</text>
        </view>
        <LightSelector title="考试体系" :options="categoryNames" :value="categoryIndex" @change="onCategoryChange">
          <view class="picker-row">
            <text>考试体系</text>
            <text class="picker-row__value">{{ selectedCategoryName }}</text>
          </view>
        </LightSelector>
        <LightSelector :title="regionLevelLabel" :options="regionNames" :value="regionIndex" @change="onRegionChange">
          <view class="picker-row">
            <text>{{ regionLevelLabel }}</text>
            <text class="picker-row__value">{{ selectedRegionName }}</text>
          </view>
        </LightSelector>
        <LightSelector v-if="hasDirectionLevel" :title="directionLevelLabel" :options="directionNames" :value="directionIndex" @change="onDirectionChange">
          <view class="picker-row picker-row--last">
            <text>{{ directionLevelLabel }}</text>
            <text class="picker-row__value">{{ selectedDirectionName }}</text>
          </view>
        </LightSelector>
      </view>

      <view v-if="selectedTarget" class="card detail-card">
        <view class="section-head">
          <text class="section-title">{{ selectedTarget.targetName }}</text>
        </view>

        <view class="detail-tags">
          <text v-if="selectedTarget.examCategory" class="detail-tag detail-tag--blue">{{ selectedTarget.examCategory }}</text>
          <text v-if="selectedTarget.examSubcategory" class="detail-tag detail-tag--cyan">{{ selectedTarget.examSubcategory }}</text>
          <text v-if="selectedTarget.subcategory" class="detail-tag detail-tag--purple">{{ selectedTarget.subcategory }}</text>
          <text v-if="selectedTarget.subcategory2" class="detail-tag detail-tag--orange">{{ selectedTarget.subcategory2 }}</text>
          <text v-if="selectedTarget.interviewFormat" class="detail-tag detail-tag--green">{{ selectedTarget.interviewFormat }}</text>
          <text v-if="selectedTarget.timingMode" class="detail-tag detail-tag--lime">{{ selectedTarget.timingMode }}</text>
        </view>

        <text v-if="selectedHint" class="admin-hint">{{ selectedHint }}</text>

        <view class="detail-table">
          <view class="detail-row">
            <text class="detail-row__label">入口编码</text>
            <text class="detail-row__value">{{ selectedTarget.targetCode }}</text>
          </view>
          <view class="detail-row">
            <text class="detail-row__label">省份</text>
            <text class="detail-row__value">{{ selectedTarget.province || 'all' }}</text>
          </view>
          <view class="detail-row">
            <text class="detail-row__label">考试大类</text>
            <text class="detail-row__value">{{ selectedTarget.examCategory || '-' }}</text>
          </view>
          <view class="detail-row">
            <text class="detail-row__label">二级分类</text>
            <text class="detail-row__value">{{ selectedTarget.examSubcategory || '-' }}</text>
          </view>
          <view class="detail-row">
            <text class="detail-row__label">三级分类</text>
            <text class="detail-row__value">{{ selectedTarget.subcategory || '-' }}</text>
          </view>
          <view class="detail-row">
            <text class="detail-row__label">四级分类</text>
            <text class="detail-row__value">{{ selectedTarget.subcategory2 || '-' }}</text>
          </view>
          <view class="detail-row">
            <text class="detail-row__label">年份</text>
            <text class="detail-row__value">{{ selectedTarget.year || '-' }}</text>
          </view>
          <view class="detail-row">
            <text class="detail-row__label">题量</text>
            <text class="detail-row__value">{{ selectedTarget.questionCount ? `${selectedTarget.questionCount}题` : '-' }}</text>
          </view>
          <view class="detail-row">
            <text class="detail-row__label">计时模式</text>
            <text class="detail-row__value">{{ selectedTarget.timingMode || selectedTarget.interviewFormat || '-' }}</text>
          </view>
          <view class="detail-row">
            <text class="detail-row__label">题型范围</text>
            <text class="detail-row__value">{{ selectedTarget.questionTypeScope || '-' }}</text>
          </view>
        </view>

        <view class="detail-actions">
          <button class="secondary-button" @tap="goQuestionList">修改已有题目</button>
          <button class="primary-button" @tap="createQuestion">新增匹配题目</button>
          <button class="secondary-button" :loading="uploading" @tap="uploadQuestions">批量导入上传</button>
        </view>

        <button class="secondary-button copy-btn" @tap="copyPayload">复制入口字段</button>

        <view class="focus-editor">
          <view class="focus-editor__head">
            <view>
              <text class="focus-editor__title">重点分析发布内容</text>
              <text class="focus-editor__desc">保存后，用户端优先展示这里发布的内容；停用后恢复题库自动统计。</text>
            </view>
            <text class="focus-status" :class="focusConfig?.enabled ? 'focus-status--on' : 'focus-status--off'">
              {{ focusConfig?.enabled ? '已发布' : '自动统计' }}
            </text>
          </view>

          <text v-if="focusEditor.isFallback" class="focus-warning">
            当前入口暂无足够题库数据，可先补充题库，或发布管理员维护内容。
          </text>

          <view class="focus-field">
            <text class="focus-field__label">匹配题量</text>
            <input v-model="focusEditor.questionCount" class="field focus-field__input" type="number" />
          </view>

          <view class="focus-block">
            <view class="focus-block__head">
              <text class="focus-block__title">核心能力与权重</text>
              <text class="muted" @tap="addCoreFocus">+ 添加能力</text>
            </view>
            <view v-for="(item, index) in focusEditor.coreFocus" :key="'core-'+index" class="focus-editor-row">
              <input v-model="item.name" class="field" placeholder="能力名称" />
              <view class="focus-editor-row__weight">
                <input v-model="item.weight" class="field" type="number" placeholder="权重" />
                <text>%</text>
              </view>
              <input v-model="item.desc" class="field" placeholder="分析说明" />
              <text class="muted focus-editor-row__del" @tap="removeCoreFocus(index)">删除</text>
            </view>
          </view>

          <view class="focus-block">
            <view class="focus-block__head">
              <text class="focus-block__title">高频题型</text>
              <text class="muted" @tap="addHighFreqType">+ 添加题型</text>
            </view>
            <view v-for="(item, index) in focusEditor.highFreqTypes" :key="'type-'+index" class="focus-editor-row">
              <input v-model="item.type" class="field" placeholder="题型名称" />
              <picker :range="['高','中','低']" :value="['高','中','低'].indexOf(item.frequency)" @change="(e) => { item.frequency = ['高','中','低'][Number(e.detail.value)] }">
                <view class="field focus-editor-row__freq-picker">
                  <text>{{ item.frequency || '中' }}</text>
                </view>
              </picker>
              <input v-model="item.questionCount" class="field" type="number" placeholder="题量" />
              <input v-model="item.example" class="field" placeholder="示例或说明" />
              <text class="muted focus-editor-row__del" @tap="removeHighFreqType(index)">删除</text>
            </view>
          </view>

          <view class="focus-field">
            <text class="focus-field__label">热门话题</text>
            <textarea v-model="hotTopicsText" class="field focus-textarea" placeholder="一行一个话题" />
          </view>

          <view class="focus-field">
            <text class="focus-field__label">备考策略</text>
            <textarea v-model="strategyText" class="field focus-textarea" placeholder="一行一条策略" />
          </view>

          <view class="focus-actions">
            <button class="secondary-button" @tap="loadFocusEditor(true)">载入自动统计</button>
            <button class="primary-button" :loading="focusSaving" @tap="saveFocusEditor">保存并发布</button>
            <button class="secondary-button secondary-button--danger" :disabled="!focusConfig" @tap="disableFocusEditor">停用发布</button>
          </view>
        </view>
      </view>

      <view v-else class="card">
        <EmptyState title="请选择一个定向入口" desc="先选择考试体系、地区来源和方向。" />
      </view>
    </template>
  </view>
</template>

<script setup>
import { computed, ref, watch } from 'vue'
import { onShow } from '@dcloudio/uni-app'
import EmptyState from '../../components/EmptyState.vue'
import LightSelector from '../../components/LightSelector.vue'
import { importQuestions } from '../../api/questionBank'
import { getFocusAdminConfig, saveFocusAdminConfig, disableFocusAdminConfig } from '../../api/targeted'
import { useTargetedStore } from '../../stores/targeted'
import { useUserStore } from '../../stores/user'
import { getTargetMaintenanceHint, mergeTargetPayload } from '../../utils/targetedOptions'
import { hideLoading, requireLogin, showLoading, toast } from '../../utils/navigation'

const targetedStore = useTargetedStore()
const userStore = useUserStore()
const selectedCategoryId = ref('')
const selectedRegionId = ref('')
const selectedTargetCode = ref('')
const uploading = ref(false)
const focusLoading = ref(false)
const focusSaving = ref(false)
const focusConfig = ref(null)
const focusEditor = ref(createBlankFocusEditor())
const hotTopicsText = ref('')
const strategyText = ref('')

const positionTree = computed(() => targetedStore.positionTree || [])
const selectedCategory = computed(() => positionTree.value.find((item) => item.id === selectedCategoryId.value) || positionTree.value[0] || null)
const levelLabels = computed(() => selectedCategory.value?.levelLabels || {})
const regionLevelLabel = computed(() => levelLabels.value.region || '地区 / 来源')
const directionLevelLabel = computed(() => levelLabels.value.direction || '方向')
const currentRegions = computed(() => selectedCategory.value?.children || [])
const selectedRegion = computed(() => currentRegions.value.find((item) => item.id === selectedRegionId.value) || currentRegions.value[0] || null)
const currentDirections = computed(() => selectedRegion.value?.directions || [])
const hasDirectionLevel = computed(() => currentDirections.value.length > 0)
const selectedDirection = computed(() => (
  selectedTargetCode.value
    ? currentDirections.value.find((item) => item.id === selectedTargetCode.value) || null
    : null
))
const categoryNames = computed(() => positionTree.value.map((item) => item.name))
const regionNames = computed(() => currentRegions.value.map((item) => item.name))
const directionNames = computed(() => ['不限', ...currentDirections.value.map((item) => item.name)])
const categoryIndex = computed(() => Math.max(0, positionTree.value.findIndex((item) => item.id === selectedCategoryId.value)))
const regionIndex = computed(() => Math.max(0, currentRegions.value.findIndex((item) => item.id === selectedRegionId.value)))
const directionIndex = computed(() => {
  const index = currentDirections.value.findIndex((item) => item.id === selectedTargetCode.value)
  return index >= 0 ? index + 1 : 0
})
const selectedCategoryName = computed(() => selectedCategory.value?.name || '请选择')
const selectedRegionName = computed(() => selectedRegion.value?.name || '请选择')
const selectedDirectionName = computed(() => selectedDirection.value?.name || '不限')
const selectedTarget = computed(() => (
  selectedCategory.value && selectedRegion.value
    ? mergeTargetPayload(selectedCategory.value, selectedRegion.value, selectedDirection.value || {})
    : null
))
const selectedHint = computed(() => getTargetMaintenanceHint(selectedTarget.value || {}))

onShow(async () => {
  if (!requireLogin()) return
  await userStore.loadUserInfo().catch(() => null)
  await targetedStore.fetchPositionTree().catch(() => null)
  if (!selectedTargetCode.value) selectCategory(positionTree.value[0])
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
      toast('已载入题库自动统计结果', 'success')
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
    toast('重点分析已发布', 'success')
  } finally {
    focusSaving.value = false
  }
}

async function disableFocusEditor() {
  if (!selectedTarget.value?.targetCode) return
  await disableFocusAdminConfig({ target: queryFromTarget() })
  focusConfig.value = null
  await loadFocusEditor(true)
  toast('已停用发布内容，恢复自动统计', 'success')
}

function applySelection(category, region, direction) {
  if (!category || !region) return
  selectedCategoryId.value = category.id
  selectedRegionId.value = region.id
  selectedTargetCode.value = direction?.id || direction?.code || ''
}

function selectCategory(category) {
  const region = category?.children?.[0]
  applySelection(category, region, null)
}

function selectRegion(region) {
  applySelection(selectedCategory.value, region, null)
}

function selectDirection(direction) {
  selectedTargetCode.value = direction?.id || direction?.code || ''
}

function onCategoryChange(event) {
  selectCategory(positionTree.value[Number(event.detail.value)])
}

function onRegionChange(event) {
  selectRegion(currentRegions.value[Number(event.detail.value)])
}

function onDirectionChange(event) {
  const index = Number(event.detail.value)
  selectDirection(index <= 0 ? null : currentDirections.value[index - 1])
}

function queryFromTarget() {
  const query = Object.fromEntries(
    Object.entries(selectedTarget.value || {})
      .filter(([, value]) => value !== undefined && value !== null && String(value).trim() !== '')
  )
  if (query.province === 'all') query.province = 'national'
  return query
}

function targetQueryString() {
  return Object.entries(queryFromTarget())
    .map(([key, value]) => `${encodeURIComponent(key)}=${encodeURIComponent(value)}`)
    .join('&')
}

function goQuestionList() {
  uni.navigateTo({ url: '/pages/admin/questions' })
}

function createQuestion() {
  const query = targetQueryString()
  uni.navigateTo({ url: `/pages/admin/question-edit${query ? `?${query}` : ''}` })
}

function copyPayload() {
  const text = JSON.stringify(queryFromTarget(), null, 2)
  uni.setClipboardData({
    data: text,
    success() {
      toast('入口字段已复制', 'success')
    }
  })
}

function chooseImportFile() {
  return new Promise((resolve, reject) => {
    if (!uni.chooseMessageFile) {
      reject(new Error('当前环境不支持文件选择，请在 PC 管理端批量导入'))
      return
    }
    uni.chooseMessageFile({
      count: 1,
      type: 'file',
      extension: ['xlsx', 'xls', 'docx', 'doc'],
      success(res) {
        resolve(res.tempFiles?.[0]?.path || '')
      },
      fail(error) {
        reject(error)
      }
    })
  })
}

async function uploadQuestions() {
  if (uploading.value) return
  uploading.value = true
  showLoading('上传题库')
  try {
    const filePath = await chooseImportFile()
    if (!filePath) {
      toast('未选择文件')
      return
    }
    const response = await importQuestions(filePath)
    const imported = response?.imported ?? response?.successCount ?? 0
    const failed = response?.failed ?? response?.failedCount ?? 0
    toast(`导入完成：成功 ${imported} 道，失败 ${failed} 道`, 'success')
  } catch (error) {
    toast(error?.message || '上传导入失败')
  } finally {
    uploading.value = false
    hideLoading()
  }
}
</script>

<style scoped>
.admin-header {
  margin-bottom: 8rpx;
}

.picker-card {
  padding-bottom: 18rpx;
}

.picker-row {
  display: flex;
  justify-content: space-between;
  gap: 24rpx;
  padding: 22rpx 0;
  border-bottom: 1rpx solid #eef2f6;
  color: #2a3648;
  font-size: 27rpx;
}

.picker-row--last {
  border-bottom: 0;
}

.picker-row__value {
  max-width: 420rpx;
  color: #2F7FD6;
  text-align: right;
}

.admin-hint {
  display: block;
  margin-top: 8rpx;
  color: #64748B;
  font-size: 24rpx;
  line-height: 1.6;
}

.detail-card {
  margin-top: 16rpx;
}

.detail-tags {
  display: flex;
  flex-wrap: wrap;
  gap: 10rpx;
  margin-bottom: 12rpx;
}

.detail-tag {
  padding: 6rpx 14rpx;
  border-radius: 999rpx;
  font-size: 22rpx;
  font-weight: 500;
}

.detail-tag--blue { background: rgba(24, 144, 255, 0.1); color: #1890ff; }
.detail-tag--cyan { background: rgba(19, 194, 194, 0.1); color: #13c2c2; }
.detail-tag--purple { background: rgba(114, 46, 209, 0.1); color: #722ed1; }
.detail-tag--orange { background: rgba(250, 140, 22, 0.1); color: #d48806; }
.detail-tag--green { background: rgba(82, 196, 26, 0.1); color: #389e0d; }
.detail-tag--lime { background: rgba(160, 217, 17, 0.1); color: #7cb305; }

.detail-table {
  margin-top: 12rpx;
  border: 1rpx solid #eef2f6;
  border-radius: 12rpx;
  overflow: hidden;
}

.detail-row {
  display: flex;
  padding: 16rpx 20rpx;
  border-bottom: 1rpx solid #eef2f6;
}

.detail-row:last-child {
  border-bottom: 0;
}

.detail-row__label {
  width: 160rpx;
  color: #64748B;
  font-size: 24rpx;
  flex-shrink: 0;
}

.detail-row__value {
  color: #2a3648;
  font-size: 24rpx;
  word-break: break-all;
}

.detail-actions {
  display: grid;
  gap: 14rpx;
  margin-top: 20rpx;
}

.detail-actions button {
  width: 100%;
  box-sizing: border-box;
}

.copy-btn {
  width: 100%;
  margin-top: 14rpx;
}

.focus-editor {
  margin-top: 28rpx;
  padding-top: 22rpx;
  border-top: 1rpx solid #eef2f6;
}

.focus-editor__head {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 16rpx;
  margin-bottom: 16rpx;
}

.focus-editor__title {
  display: block;
  color: #172033;
  font-size: 28rpx;
  font-weight: 700;
}

.focus-editor__desc {
  display: block;
  margin-top: 4rpx;
  color: #64748B;
  font-size: 22rpx;
}

.focus-status {
  padding: 8rpx 16rpx;
  border-radius: 999rpx;
  font-size: 22rpx;
  flex-shrink: 0;
}

.focus-status--on { background: #f6ffed; color: #389e0d; }
.focus-status--off { background: #f5f5f5; color: #8c8c8c; }

.focus-warning {
  display: block;
  margin-bottom: 16rpx;
  padding: 16rpx 20rpx;
  border-radius: 12rpx;
  background: #fffbe6;
  border: 1rpx solid #ffe58f;
  color: #8c6d1f;
  font-size: 24rpx;
  line-height: 1.5;
}

.focus-field {
  display: flex;
  align-items: center;
  gap: 16rpx;
  margin-top: 16rpx;
}

.focus-field__label {
  width: 140rpx;
  color: #64748B;
  font-size: 24rpx;
  font-weight: 600;
  flex-shrink: 0;
}

.focus-field__input {
  flex: 1;
}

.focus-textarea {
  flex: 1;
  min-height: 120rpx;
}

.focus-block {
  margin-top: 22rpx;
}

.focus-block__head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 12rpx;
}

.focus-block__title {
  color: #2a3648;
  font-size: 26rpx;
  font-weight: 700;
}

.focus-editor-row {
  display: flex;
  flex-wrap: wrap;
  gap: 10rpx;
  margin-bottom: 12rpx;
  padding: 16rpx;
  border-radius: 12rpx;
  background: #fafbfc;
  border: 1rpx solid #eef2f6;
}

.focus-editor-row .field {
  flex: 1;
  min-width: 140rpx;
}

.focus-editor-row__weight {
  display: flex;
  align-items: center;
  gap: 6rpx;
  width: 140rpx;
}

.focus-editor-row__weight .field {
  flex: 1;
  min-width: 0;
}

.focus-editor-row__freq-picker {
  width: 100rpx;
  padding: 12rpx 16rpx;
  border: 1rpx solid #d9d9d9;
  border-radius: 8rpx;
  text-align: center;
}

.focus-editor-row__del {
  flex-shrink: 0;
  align-self: center;
}

.focus-actions {
  display: flex;
  flex-wrap: wrap;
  justify-content: flex-end;
  gap: 12rpx;
  margin-top: 22rpx;
}

.secondary-button--danger {
  color: #cf1322;
  border-color: #ffa39e;
}
</style>
