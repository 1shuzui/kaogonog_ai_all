<template>
  <div class="focus-page page-container">
    <div class="focus-header">
      <a-button type="text" @click="$router.back()">
        <LeftOutlined /> 返回
      </a-button>
      <h2>面试重点分析</h2>
    </div>

    <div class="focus-selection card">
      <span class="focus-tag">{{ provinceName }}</span>
      <span class="focus-tag">{{ positionName }}</span>
    </div>

    <a-spin :spinning="targetedStore.focusLoading" tip="AI正在分析面试重点...">
      <template v-if="focusData">
        <!-- 核心考察能力 -->
        <div class="card focus-section">
          <h3><AimOutlined /> 核心考察能力</h3>
          <div v-for="item in focusData.coreFocus" :key="item.name" class="focus-ability">
            <div class="focus-ability__header">
              <span class="focus-ability__name">{{ item.name }}</span>
              <span class="focus-ability__weight">{{ item.weight }}%</span>
            </div>
            <a-progress :percent="item.weight" :show-info="false" :stroke-color="primaryColor" size="small" />
            <p class="focus-ability__desc">{{ item.desc }}</p>
          </div>
        </div>

        <!-- 高频题型 -->
        <div class="card focus-section">
          <h3><BarChartOutlined /> 高频题型</h3>
          <div v-for="item in focusData.highFreqTypes" :key="item.type" class="freq-type">
            <div class="freq-type__header">
              <span class="freq-type__name">{{ item.type }}</span>
              <a-tag :color="freqColor(item.frequency)">{{ item.frequency }}频</a-tag>
            </div>
            <p class="freq-type__example">{{ item.example }}</p>
          </div>
        </div>

        <!-- 热门话题 -->
        <div class="card focus-section">
          <h3><FireOutlined /> 热门话题</h3>
          <div class="hot-topics">
            <a-tag v-for="topic in focusData.hotTopics" :key="topic" color="orange">{{ topic }}</a-tag>
          </div>
        </div>

        <!-- 备考策略 -->
        <div class="card focus-section">
          <h3><BulbOutlined /> 备考策略</h3>
          <div v-for="(s, idx) in focusData.strategy" :key="idx" class="strategy-item">
            <div class="strategy-item__num">{{ idx + 1 }}</div>
            <span>{{ s }}</span>
          </div>
        </div>

        <!-- 开始练习 -->
        <div class="focus-actions">
          <a-button
            type="primary"
            size="large"
            block
            :loading="targetedStore.generateLoading"
            @click="startTargetedPractice"
          >
            <ThunderboltOutlined /> 生成针对性题目并开始练习
          </a-button>
        </div>
      </template>

      <EmptyState v-else-if="!targetedStore.focusLoading" text="暂无分析数据，请返回选择省份和岗位" />
    </a-spin>
  </div>
</template>

<script setup>
import { computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { LeftOutlined, AimOutlined, BarChartOutlined, FireOutlined, BulbOutlined, ThunderboltOutlined } from '@ant-design/icons-vue'
import { useTargetedStore } from '@/stores/targeted'
import { PROVINCES, POSITION_SYSTEMS } from '@/utils/constants'
import EmptyState from '@/components/common/EmptyState.vue'

const router = useRouter()
const targetedStore = useTargetedStore()
const primaryColor = '#1B5FAA'

const focusData = computed(() => targetedStore.focusData)

const provinceName = computed(() => {
  const p = PROVINCES.find(p => p.code === targetedStore.selectedProvince)
  return p ? p.name : targetedStore.selectedProvince
})

const positionName = computed(() => {
  const p = POSITION_SYSTEMS.find(p => p.code === targetedStore.selectedPosition)
  return p ? p.name : targetedStore.selectedPosition
})

function freqColor(freq) {
  if (freq === '高') return 'red'
  if (freq === '中') return 'orange'
  return 'default'
}

onMounted(() => {
  if (targetedStore.hasSelection && !targetedStore.focusData) {
    targetedStore.fetchFocusAnalysis()
  }
  if (!targetedStore.hasSelection) {
    router.replace('/targeted')
  }
})

async function startTargetedPractice() {
  await targetedStore.fetchGeneratedQuestions(5)
  if (targetedStore.generatedQuestions.length) {
    router.push({ path: '/exam/prepare', query: { source: 'targeted' } })
  }
}
</script>

<style lang="less" scoped>
@import '@/styles/variables.less';

.focus-header {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 16px;

  h2 {
    font-size: @font-size-xl;
    color: @text-primary;
    margin: 0;
  }
}

.focus-selection {
  display: flex;
  gap: 8px;
  padding: 12px 16px;
  margin-bottom: 16px;
}

.focus-tag {
  padding: 4px 12px;
  border-radius: 16px;
  background: @bg-light-blue;
  color: @primary-color;
  font-size: @font-size-sm;
  font-weight: 500;
}

.focus-section {
  padding: 16px;
  margin-bottom: 12px;

  h3 {
    font-size: @font-size-lg;
    color: @text-primary;
    margin-bottom: 14px;
    display: flex;
    align-items: center;
    gap: 6px;
  }
}

.focus-ability {
  margin-bottom: 14px;

  &:last-child {
    margin-bottom: 0;
  }
}

.focus-ability__header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 4px;
}

.focus-ability__name {
  font-size: @font-size-base;
  color: @text-regular;
  font-weight: 500;
}

.focus-ability__weight {
  font-size: @font-size-sm;
  color: @primary-color;
  font-weight: 600;
}

.focus-ability__desc {
  font-size: @font-size-xs;
  color: @text-secondary;
  margin-top: 4px;
  margin-bottom: 0;
}

.freq-type {
  margin-bottom: 14px;
  padding-bottom: 14px;
  border-bottom: 1px solid @divider-color;

  &:last-child {
    margin-bottom: 0;
    padding-bottom: 0;
    border-bottom: none;
  }
}

.freq-type__header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 6px;
}

.freq-type__name {
  font-size: @font-size-base;
  color: @text-regular;
  font-weight: 500;
}

.freq-type__example {
  font-size: @font-size-sm;
  color: @text-secondary;
  margin: 0;
  line-height: 1.5;
}

.hot-topics {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.strategy-item {
  display: flex;
  align-items: flex-start;
  gap: 10px;
  margin-bottom: 12px;
  font-size: @font-size-base;
  color: @text-regular;
  line-height: 1.5;

  &:last-child {
    margin-bottom: 0;
  }
}

.strategy-item__num {
  width: 24px;
  height: 24px;
  border-radius: 50%;
  background: @primary-color;
  color: #fff;
  font-size: @font-size-xs;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
}

.focus-actions {
  margin-top: 8px;
  margin-bottom: 16px;
}
</style>
