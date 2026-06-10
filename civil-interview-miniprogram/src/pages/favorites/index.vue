<!--
小程序错题本和收藏夹共用一个复盘入口，但低分题来自评分结果，收藏题来自用户手动操作，二者不能在端侧互相推断。
这里保留“再练一次”和移除能力，方便移动端复盘；真实题目、权益消耗和练习创建仍由后端流程确认。

@param: 无；页面读取收藏 store 中的错题、收藏和计数状态。
@return: 渲染复盘列表、分组 tab、清空确认和进入练习的跳转入口。
@raises: 不主动抛业务异常；接口失败、未登录和权限不足由请求层或页面提示承接。
-->
<template>
  <view class="page">
    <text class="page-title">错题本 / 收藏夹</text>
    <text class="page-desc">低分题自动进入错题，手动收藏单独记录。</text>

    <view class="tabs card">
      <view
        v-for="tab in tabs"
        :key="tab.key"
        class="tab-item"
        :class="{ 'tab-item--active': activeTab === tab.key }"
        @tap="activeTab = tab.key"
      >
        {{ tab.label }} {{ tab.count }}
      </view>
    </view>

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
          <button class="secondary-button" @tap="practice(item)">再练一次</button>
          <button class="secondary-button danger-button" @tap="remove(item)">移除</button>
        </view>
      </view>
    </view>
    <view v-else class="card">
      <EmptyState :title="emptyTitle" desc="完成测评或手动收藏后会出现在这里。" />
    </view>

    <button v-if="favoritesStore.count" class="secondary-button danger-button clear-button" @tap="confirmClear">
      清空错题与收藏
    </button>
  </view>
</template>

<script setup>
import { computed, ref } from 'vue'
import EmptyState from '../../components/EmptyState.vue'
import { useFavoritesStore } from '../../stores/favorites'
import { formatDate } from '../../utils/format'

const favoritesStore = useFavoritesStore()
const activeTab = ref('all')

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
    content: '将清除本机错题与收藏记录，不会删除服务器历史测评。',
    confirmText: '确认清空',
    confirmColor: '#cf1322',
    success(res) {
      if (res.confirm) favoritesStore.clearAll()
    }
  })
}
</script>

<style scoped>
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
  font-weight: 800;
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
