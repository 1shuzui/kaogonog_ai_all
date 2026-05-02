<template>
  <div class="favorites-page page-container">
    <h2>错题本</h2>

    <!-- Tab 切换 -->
    <a-radio-group v-model:value="activeTab" button-style="solid" style="margin-bottom: 16px">
      <a-radio-button value="all">全部 ({{ favoritesStore.count }})</a-radio-button>
      <a-radio-button value="weak">低分题 ({{ favoritesStore.weakItems.length }})</a-radio-button>
      <a-radio-button value="starred">收藏题 ({{ favoritesStore.starredItems.length }})</a-radio-button>
    </a-radio-group>

    <!-- 列表 -->
    <div v-if="filteredItems.length">
      <div
        v-for="item in filteredItems"
        :key="item.id"
        class="fav-item card"
      >
        <div class="fav-item__header">
          <a-tag :color="dimensionColor(item.dimension)" size="small">
            {{ dimensionName(item.dimension) }}
          </a-tag>
          <a-tag v-if="item.type === 'weak'" color="red" size="small">低分</a-tag>
          <a-tag v-else color="gold" size="small">
            <StarFilled /> 收藏
          </a-tag>
          <span class="fav-item__date">{{ formatDate(item.addedAt) }}</span>
        </div>

        <div class="fav-item__stem">{{ item.questionStem }}</div>

        <div class="fav-item__footer">
          <div class="fav-item__score">
            <span>得分：</span>
            <span :style="{ color: scoreColor(item.score, item.maxScore), fontWeight: 600 }">
              {{ item.score }}/{{ item.maxScore }}
            </span>
            <span v-if="item.retryCount > 0" class="fav-item__retry">
              · 重做 {{ item.retryCount }} 次
              <span v-if="item.bestRetryScore !== null" style="color: #389E0D">
                最高 {{ item.bestRetryScore }}
              </span>
            </span>
          </div>
          <a-space>
            <a-button size="small" type="primary" @click="retryQuestion(item)">
              <RedoOutlined /> 重做
            </a-button>
            <a-popconfirm title="确定删除？" @confirm="favoritesStore.removeItem(item.id)">
              <a-button size="small" danger>
                <DeleteOutlined />
              </a-button>
            </a-popconfirm>
          </a-space>
        </div>
      </div>
    </div>
    <EmptyState v-else :text="emptyText" />

    <!-- 底部清空 -->
    <div v-if="favoritesStore.count > 0" style="text-align: center; margin-top: 16px; padding-bottom: 16px">
      <a-popconfirm title="确定清空所有错题？此操作不可恢复。" @confirm="favoritesStore.clearAll()">
        <a-button type="text" danger size="small">清空全部</a-button>
      </a-popconfirm>
    </div>
  </div>
</template>

<script setup>
import { ref, computed } from 'vue'
import { useRouter } from 'vue-router'
import { StarFilled, RedoOutlined, DeleteOutlined } from '@ant-design/icons-vue'
import { useFavoritesStore } from '@/stores/favorites'
import { useExamStore } from '@/stores/exam'
import { getQuestionTypeName } from '@/utils/constants'
import { formatDate } from '@/utils/formatter'
import { getQuestionById } from '@/api/questionBank'
import EmptyState from '@/components/common/EmptyState.vue'

const router = useRouter()
const favoritesStore = useFavoritesStore()
const examStore = useExamStore()
const activeTab = ref('all')

const filteredItems = computed(() => {
  if (activeTab.value === 'weak') return favoritesStore.weakItems
  if (activeTab.value === 'starred') return favoritesStore.starredItems
  return favoritesStore.items
})

const emptyText = computed(() => {
  if (activeTab.value === 'weak') return '没有低分题目，继续保持！'
  if (activeTab.value === 'starred') return '还没有收藏任何题目'
  return '错题本为空，快去练习吧'
})

function dimensionName(key) {
  return getQuestionTypeName(key)
}

function dimensionColor(key) {
  const colors = { legal: 'purple', practical: 'green', logic: 'blue', expression: 'cyan', analysis: 'orange', emergency: 'red' }
  return colors[key] || 'blue'
}

function scoreColor(score, maxScore) {
  const ratio = score / maxScore
  if (ratio >= 0.85) return '#389E0D'
  if (ratio >= 0.75) return '#1B5FAA'
  if (ratio >= 0.6) return '#D48806'
  return '#CF1322'
}

async function retryQuestion(item) {
  try {
    const question = await getQuestionById(item.questionId)
    await examStore.initExam([question])
    router.push('/exam/room')
  } catch {
    // 如果获取失败，跳转到准备页面
    router.push('/exam/prepare')
  }
}
</script>

<style lang="less" scoped>
@import '@/styles/variables.less';

.favorites-page h2 {
  font-size: @font-size-xl;
  color: @text-primary;
  margin-bottom: 16px;
}

.fav-item {
  padding: 14px 16px;
  margin-bottom: 8px;
}

.fav-item__header {
  display: flex;
  align-items: center;
  gap: 6px;
  margin-bottom: 8px;
}

.fav-item__date {
  margin-left: auto;
  font-size: @font-size-xs;
  color: @text-secondary;
}

.fav-item__stem {
  font-size: @font-size-base;
  color: @text-regular;
  line-height: 1.6;
  margin-bottom: 10px;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
}

.fav-item__footer {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.fav-item__score {
  font-size: @font-size-sm;
  color: @text-secondary;
}

.fav-item__retry {
  font-size: @font-size-xs;
  color: @text-secondary;
}
</style>
