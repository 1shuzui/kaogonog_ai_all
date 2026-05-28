<template>
  <view class="page">
    <text class="page-title">定向入口管理</text>
    <text class="page-desc">为定向备面入口补充真实题目。普通用户不会看到后台维护提示。</text>

    <view v-if="!userStore.isAdmin" class="card">
      <EmptyState title="无管理员权限" desc="请使用管理员账号登录后再访问。" />
    </view>

    <template v-else>
      <view class="card picker-card">
        <view class="section-head">
          <text class="section-title">选择维护范围</text>
        </view>
        <picker :range="categoryNames" :value="categoryIndex" @change="onCategoryChange">
          <view class="picker-row">
            <text>考试体系</text>
            <text class="picker-row__value">{{ selectedCategoryName }}</text>
          </view>
        </picker>
        <picker :range="regionNames" :value="regionIndex" @change="onRegionChange">
          <view class="picker-row">
            <text>{{ regionLevelLabel }}</text>
            <text class="picker-row__value">{{ selectedRegionName }}</text>
          </view>
        </picker>
        <picker v-if="hasDirectionLevel" :range="directionNames" :value="directionIndex" @change="onDirectionChange">
          <view class="picker-row picker-row--last">
            <text>{{ directionLevelLabel }}</text>
            <text class="picker-row__value">{{ selectedDirectionName }}</text>
          </view>
        </picker>
      </view>

      <view v-if="selectedTarget" class="card">
        <view class="section-head">
          <text class="section-title">{{ selectedTarget.targetName }}</text>
        </view>
        <text class="admin-hint">{{ selectedHint || '该入口可直接补充匹配题目。' }}</text>
        <view v-if="selectedModeHints.length" class="mode-hints">
          <text v-for="hint in selectedModeHints" :key="hint" class="mode-hint">{{ hint }}</text>
        </view>
      </view>

      <view v-if="selectedTarget" class="card action-card">
        <view class="section-head">
          <text class="section-title">题目维护</text>
        </view>
        <button class="secondary-button" @tap="goQuestionList">修改已有题目</button>
        <button class="primary-button" @tap="createQuestion">新增匹配题目</button>
        <button class="secondary-button" :loading="uploading" @tap="uploadQuestions">上传导入题目</button>
      </view>
    </template>
  </view>
</template>

<script setup>
import { computed, ref } from 'vue'
import { onShow } from '@dcloudio/uni-app'
import EmptyState from '../../components/EmptyState.vue'
import { importQuestions } from '../../api/questionBank'
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
const categoryNames = computed(() => positionTree.value.map((item) => item.name))
const regionNames = computed(() => currentRegions.value.map((item) => item.name))
const directionNames = computed(() => currentDirections.value.map((item) => item.name))
const categoryIndex = computed(() => Math.max(0, positionTree.value.findIndex((item) => item.id === selectedCategoryId.value)))
const regionIndex = computed(() => Math.max(0, currentRegions.value.findIndex((item) => item.id === selectedRegionId.value)))
const directionIndex = computed(() => Math.max(0, currentDirections.value.findIndex((item) => item.id === selectedTargetCode.value)))
const selectedCategoryName = computed(() => selectedCategory.value?.name || '请选择')
const selectedRegionName = computed(() => selectedRegion.value?.name || '请选择')
const selectedDirectionName = computed(() => selectedDirection.value?.name || '请选择')
const selectedTarget = computed(() => (
  selectedCategory.value && selectedRegion.value && (!hasDirectionLevel.value || selectedDirection.value)
    ? mergeTargetPayload(selectedCategory.value, selectedRegion.value, selectedDirection.value || {})
    : null
))
const selectedHint = computed(() => getTargetMaintenanceHint(selectedTarget.value || {}))
const selectedModeHints = computed(() => {
  const target = selectedTarget.value || {}
  return [
    target.interviewFormat ? `形式：${target.interviewFormat}` : '',
    target.questionCount ? `题量：${target.questionCount}题` : '',
    target.timingMode ? `计时：${target.timingMode}` : '',
    target.questionTypeScope ? `题型：${target.questionTypeScope}` : ''
  ].filter(Boolean)
})

onShow(async () => {
  if (!requireLogin()) return
  await userStore.loadUserInfo().catch(() => null)
  await targetedStore.fetchPositionTree().catch(() => null)
  if (!selectedTargetCode.value) selectCategory(positionTree.value[0])
})

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

function onCategoryChange(event) {
  selectCategory(positionTree.value[Number(event.detail.value)])
}

function onRegionChange(event) {
  selectRegion(currentRegions.value[Number(event.detail.value)])
}

function onDirectionChange(event) {
  selectDirection(currentDirections.value[Number(event.detail.value)])
}

function targetQuery() {
  const payload = { ...(selectedTarget.value || {}) }
  if (payload.province === 'all') payload.province = 'national'
  return Object.entries(payload)
    .filter(([, value]) => value !== undefined && value !== null && String(value).trim() !== '')
    .map(([key, value]) => `${encodeURIComponent(key)}=${encodeURIComponent(value)}`)
    .join('&')
}

function goQuestionList() {
  uni.navigateTo({ url: '/pages/admin/questions' })
}

function createQuestion() {
  const query = targetQuery()
  uni.navigateTo({ url: `/pages/admin/question-edit${query ? `?${query}` : ''}` })
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
      extension: ['xlsx', 'xls'],
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

.picker-row__value,
.admin-hint {
  display: block;
}

.picker-row__value {
  max-width: 420rpx;
  color: #1b5faa;
  text-align: right;
}

.admin-hint {
  margin-top: 8rpx;
  color: #6f7c8f;
  font-size: 24rpx;
  line-height: 1.6;
}

.action-card {
  display: grid;
  gap: 16rpx;
}

.action-card button {
  width: 100%;
  box-sizing: border-box;
  white-space: normal;
  line-height: 1.35;
}

.mode-hints {
  display: flex;
  flex-wrap: wrap;
  gap: 10rpx;
  margin-top: 14rpx;
}

.mode-hint {
  display: inline-flex;
  padding: 8rpx 12rpx;
  border-radius: 8rpx;
  background: #eef6ff;
  color: #1b5faa;
  font-size: 22rpx;
  line-height: 1.25;
}
</style>
