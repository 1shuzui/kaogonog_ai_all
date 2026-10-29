<!--
小程序错题本和收藏夹共用一个复盘入口，但低分题来自评分结果，收藏题来自用户手动操作，二者不能在端侧互相推断。
这里保留“再练一次”和移除能力，方便移动端复盘；真实题目、权益消耗和练习创建仍由后端流程确认。

@param: 无；页面读取收藏 store 中的错题、收藏和计数状态。
@return: 渲染复盘列表、分组 tab、清空确认和进入练习的跳转入口。
@raises: 不主动抛业务异常；接口失败、未登录和权限不足由请求层或页面提示承接。
-->
<template>
  <view class="motion-page page" :class="motionClass" :style="motionStyle">
    <text class="page-title">错题本 / 收藏夹</text>
    <text class="page-desc">低分题自动进入错题，手动收藏单独记录。</text>
    <button class="threshold-entry card" :disabled="settingsLoading || !!settingsError" @tap="openThreshold">
      <text>低分线设置</text>
      <view class="threshold-entry__value"><text>{{ settingsLoading ? '读取中…' : settingsError ? '读取失败' : `${thresholdPercent}%` }}</text><text>›</text></view>
    </button>
    <view v-if="settingsError" class="card" role="alert">
      <text>{{ settingsError }}</text><button class="secondary-button" @tap="loadThreshold">重新读取设置</button>
    </view>
    <LearnerSheet :show="thresholdOpen" title="低分线设置" close-label="取消" :body-height="270" @close="closeThreshold">
      <text class="threshold-hint">得分低于满分的以下比例时，自动归入低分题。等于分数线不收录。</text>
      <view class="threshold-input-row">
        <input v-model="thresholdDraft" class="field threshold-input" type="number" maxlength="3" aria-label="低分线百分比" :disabled="thresholdSaving" />
        <text>%</text>
      </view>
      <text class="threshold-hint">支持 1–100 的整数，默认 60%。保存后对已有练习生效，手动收藏和已移除记录保持原样。</text>
      <text v-if="thresholdError" class="threshold-error" role="alert">{{ thresholdError }}</text>
      <view class="threshold-actions">
        <button class="secondary-button" :disabled="thresholdSaving" @tap="resetThresholdDraft">恢复默认</button>
        <button class="primary-button" :loading="thresholdSaving" :disabled="thresholdSaving" @tap="saveThreshold">保存</button>
      </view>
    </LearnerSheet>
    <view v-if="favoritesStore.error" class="card" role="alert">
      <text>{{ favoritesStore.error }}</text><button class="secondary-button" @tap="favoritesStore.load()">重新同步</button>
    </view>
    <text v-if="favoritesStore.loading" class="page-desc">正在同步复习记录…</text>
    <text v-if="favoritesStore.migrationNotice" class="page-desc">{{ favoritesStore.migrationNotice }}</text>

    <MotionSegmented v-model="activeTab" :options="tabs.map(tab => ({ value: tab.key, label: tab.label, count: tab.count }))" />

    <view v-if="visibleItems.length" class="favorite-list">
      <view v-for="item in visibleItems" :key="item.id" class="favorite-card card">
        <view class="favorite-card__head">
          <text v-if="item.isWeak" class="tag tag--weak">低分</text>
          <text v-if="item.isStarred" class="tag tag--star">收藏</text>
          <text class="favorite-card__score">{{ item.score || 0 }}/{{ item.maxScore || 100 }}</text>
        </view>
        <text class="favorite-card__stem">{{ item.questionStem || '题目内容暂缺' }}</text>
        <view class="favorite-card__meta">
          <text>{{ item.dimension || '综合训练' }}</text>
          <text>{{ formatDate(item.date || item.addedAt) }}</text>
        </view>
        <view class="favorite-card__actions">
          <button class="secondary-button" :disabled="!item.canPractice" @tap="practice(item)">再练一次</button>
          <button class="secondary-button danger-button" :disabled="favoritesStore.saving" @tap="remove(item)">移除</button>
        </view>
      </view>
    </view>
    <view v-else-if="!favoritesStore.loading && !favoritesStore.error" class="card">
      <EmptyState :title="emptyTitle" desc="完成测评或手动收藏后会出现在这里。" />
    </view>

    <button v-if="favoritesStore.count" class="secondary-button danger-button clear-button" :disabled="favoritesStore.saving" @tap="confirmClear">
      清空错题与收藏
    </button>
  </view>
</template>

<script setup>
import MotionSegmented from '../../components/MotionSegmented.vue'
import LearnerSheet from '../../components/LearnerSheet.vue'
import { useUserStore } from '../../stores/user'
import { promptLoginForAction, toast } from '../../utils/navigation'
import { usePageMotion } from '../../motion/useMotion'
const { motionClass, motionStyle } = usePageMotion()
import { computed, ref } from 'vue'
import { onShow } from '@dcloudio/uni-app'
import EmptyState from '../../components/EmptyState.vue'
import { useFavoritesStore } from '../../stores/favorites'
import { formatDate } from '../../utils/format'

const favoritesStore = useFavoritesStore()
const activeTab = ref('all')
const userStore = useUserStore()
const settingsLoading = ref(true)
const settingsError = ref('')
const thresholdOpen = ref(false)
const thresholdDraft = ref('60')
const thresholdError = ref('')
const thresholdSaving = ref(false)
const thresholdPercent = computed(() => userStore.preferences.reviewWeakThresholdPercent ?? 60)

async function loadThreshold() {
  const token = userStore.token
  settingsLoading.value = true
  settingsError.value = ''
  try {
    await userStore.loadUserInfo()
  } catch (error) {
    if (userStore.token === token) settingsError.value = error?.message || '低分线读取失败，请重试'
  } finally {
    if (userStore.token === token) settingsLoading.value = false
  }
}

onShow(() => {
  thresholdOpen.value = false
  if (!promptLoginForAction('查看错题与收藏', '/pages/favorites/index')) return
  loadThreshold()
  favoritesStore.load()
})

function openThreshold() {
  thresholdDraft.value = String(thresholdPercent.value)
  thresholdError.value = ''
  thresholdOpen.value = true
}

function closeThreshold() {
  if (!thresholdSaving.value) thresholdOpen.value = false
}

function resetThresholdDraft() {
  thresholdDraft.value = '60'
  thresholdError.value = ''
}

async function saveThreshold() {
  if (thresholdSaving.value) return
  const raw = String(thresholdDraft.value).trim()
  const percent = Number(raw)
  if (!/^\d{1,3}$/.test(raw) || percent < 1 || percent > 100) {
    thresholdError.value = '请输入 1–100 的整数百分比'
    return
  }
  const token = userStore.token
  thresholdSaving.value = true
  thresholdError.value = ''
  try {
    await userStore.saveReviewWeakThreshold(percent)
    const refreshed = await favoritesStore.load()
    if (userStore.token !== token) return
    thresholdOpen.value = false
    if (!refreshed) favoritesStore.error = '低分线已保存，列表刷新失败，请重新同步。'
    toast('低分线已保存', 'success')
  } catch (error) {
    if (userStore.token === token) thresholdError.value = `未保存：${error?.message || '请重试'}`
  } finally {
    thresholdSaving.value = false
  }
}

const tabs = computed(() => [
  { key: 'all', label: '全部', count: favoritesStore.count },
  { key: 'weak', label: '低分题', count: favoritesStore.weakItems.length },
  { key: 'starred', label: '收藏题', count: favoritesStore.starredItems.length }
])

const visibleItems = computed(() => {
  if (activeTab.value === 'weak') return favoritesStore.weakItems
  if (activeTab.value === 'starred') return favoritesStore.starredItems
  return favoritesStore.items.filter((item) => item.isWeak || item.isStarred)
})

const emptyTitle = computed(() => {
  if (activeTab.value === 'weak') return '暂无低分题'
  if (activeTab.value === 'starred') return '暂无收藏题'
  return '错题本为空'
})

function practice(item) {
  if (!item?.questionId) return
  uni.navigateTo({ url: `/pages/bank/detail?id=${encodeURIComponent(item.questionId)}` })
}

function remove(item) {
  if (!item?.id) return
  favoritesStore.removeItem(item.id, activeTab.value === 'all' ? 'all' : activeTab.value)
}

function confirmClear() {
  uni.showModal({
    title: '确认清空？',
    content: '将清空当前账号的错题与收藏，历史测评仍可查看。',
    confirmText: '确认清空',
    confirmColor: '#cf1322',
    success(res) {
      if (res.confirm) favoritesStore.clearAll()
    }
  })
}
</script>

<style scoped>
.threshold-entry {
  display: flex;
  align-items: center;
  justify-content: space-between;
  width: 100%;
  min-height: 48px;
  padding: 12px 16px;
  font-size: 15px;
  color: var(--ui-text);
  text-align: left;
}
.threshold-entry__value { display: flex; align-items: center; gap: 12px; color: var(--ui-link); }
.threshold-hint { display: block; color: var(--ui-muted); font-size: 14px; line-height: 1.6; }
.threshold-input-row { display: flex; align-items: center; gap: 12px; margin: 16px 0; }
.threshold-input { flex: 1; min-width: 0; }
.threshold-error { display: block; color: #cf1322; font-size: 14px; margin-top: 8px; }
.threshold-actions { display: flex; gap: 12px; margin-top: 16px; }
.threshold-actions button { flex: 1; }
.tabs {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 8rpx;
  padding: 8rpx;
}

.tab-item {
  padding: 18rpx 8rpx;
  border-radius: 12rpx;
  color: #64748B;
  font-size: 25rpx;
  font-weight: 800;
  text-align: center;
}

.tab-item--active {
  background: #EAF5FF;
  color: #2F7FD6;
}

.favorite-card__head,
.favorite-card__meta,
.favorite-card__actions {
  display: flex;
  align-items: center;
}

.favorite-card__head {
  gap: 10rpx;
  margin-bottom: 12rpx;
}

.favorite-card__score {
  margin-left: auto;
  color: #2F7FD6;
  font-size: 28rpx;
  font-weight: 900;
}

.tag {
  padding: 6rpx 12rpx;
  border-radius: 999rpx;
  font-size: 22rpx;
  font-weight: 800;
}

.tag--weak {
  background: #fff1f0;
  color: #cf1322;
}

.tag--star {
  background: #fffbe6;
  color: #ad6800;
}

.favorite-card__stem {
  display: block;
  color: #1f2b3d;
  font-size: 28rpx;
  font-weight: 400;
  line-height: 1.55;
}

.favorite-card__meta {
  justify-content: space-between;
  margin-top: 12rpx;
  color: #64748B;
  font-size: 23rpx;
}

.favorite-card__actions {
  gap: 14rpx;
  margin-top: 18rpx;
}

.favorite-card__actions button {
  flex: 1;
}

.clear-button {
  margin-top: 18rpx;
}
</style>
