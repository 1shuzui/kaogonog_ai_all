<!--
这个页面展示面试重点分析结果；它要区分能力维度和题型分类，数据不足时宁可空态，也不要硬凑雷达图。

@param: 无；页面运行时从 props、路由参数、Pinia 状态和用户点击中拿数据。
@return: 渲染当前业务界面，并把按钮、表单或跳转事件交给既有流程处理。
@raises: 不主动抛业务异常；接口失败、未登录和权限不足由请求层或页面提示承接。
-->
<template>
  <div class="focus-page page-container">
    <div class="focus-header">
      <a-button type="text" @click="$router.back()">
        <LeftOutlined /> 返回
      </a-button>
      <h2>面试重点分析</h2>
    </div>

    <div class="focus-selection card">
      <span v-for="tag in selectionTags" :key="tag" class="focus-tag">{{ tag }}</span>
    </div>

    <a-spin :spinning="targetedStore.focusLoading" tip="AI正在分析面试重点...">
      <template v-if="focusData">
        <EmptyState
          v-if="isEmptyFocus"
          :text="focusData.emptyMessage || '暂无足够题库数据，请选择已有真实题库的考试方向后再试。'"
        />
        <template v-else>
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
            @click="generateTargetedPractice"
          >
            <ThunderboltOutlined /> 生成针对性题目
          </a-button>
        </div>

        <div v-if="targetedStore.generatedQuestions.length" class="card focus-section generated-practice">
          <div class="generated-practice__header">
            <div>
              <h3>已生成题目</h3>
              <p>先查看题目，再点击开始练习进入设备检测和练习模式选择。</p>
            </div>
            <a-button type="primary" size="large" @click="startTargetedPractice">
              <PlayCircleOutlined /> 开始练习
            </a-button>
          </div>
          <div
            v-for="(question, index) in targetedStore.generatedQuestions"
            :key="question.id || index"
            class="generated-practice__item"
          >
            <strong>{{ index + 1 }}</strong>
            <span>{{ question.stem }}</span>
          </div>
        </div>
        </template>
      </template>

      <EmptyState v-else-if="!targetedStore.focusLoading" text="暂无分析数据，请返回选择考试方向" />
    </a-spin>
  </div>
</template>

<script setup>
import { computed, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { LeftOutlined, AimOutlined, BarChartOutlined, FireOutlined, BulbOutlined, ThunderboltOutlined, PlayCircleOutlined } from '@ant-design/icons-vue'
import { message } from 'ant-design-vue'
import { useTargetedStore } from '@/stores/targeted'
import { useUserStore } from '@/stores/user'
import { useBillingStore } from '@/stores/billing'
import { hasPremiumAccess } from '@/utils/access'
import EmptyState from '@/components/common/EmptyState.vue'

const router = useRouter()
const route = useRoute()
const targetedStore = useTargetedStore()
const userStore = useUserStore()
const billingStore = useBillingStore()
const primaryColor = '#1B5FAA'

const focusData = computed(() => targetedStore.focusData)
const hasFullAccess = computed(() => hasPremiumAccess(userStore, billingStore))
const isEmptyFocus = computed(() => (
  focusData.value?.isFallback === true || Number(focusData.value?.questionCount || 0) <= 0
))
const selectionTags = computed(() => {
  const payload = targetedStore.selectedTarget || targetedStore.selectionPayload || {}
  return [
    payload.examCategory,
    payload.examSubcategory,
    payload.subcategory || payload.subcategory2 || payload.positionType,
    payload.targetName
  ].filter((item, index, array) => item && array.indexOf(item) === index)
})

function freqColor(freq) {
  if (freq === '高') return 'red'
  if (freq === '中') return 'orange'
  return 'default'
}

function hydrateSelectionFromRoute() {
  const payload = {}
  ;[
    'province',
    'position',
    'examCategory',
    'examSubcategory',
    'subcategory',
    'subcategory2',
    'positionType',
    'targetCode',
    'targetName'
  ].forEach((key) => {
    if (typeof route.query[key] === 'string') payload[key] = route.query[key]
  })
  if (payload.targetCode || payload.examCategory || payload.targetName) {
    targetedStore.setTarget(payload)
    return
  }
  if (payload.province) {
    targetedStore.setSelection(payload.province, payload.position || '')
  }
}

onMounted(async () => {
  hydrateSelectionFromRoute()
  await userStore.loadUserInfo().catch(() => null)
  if (!hasFullAccess.value) {
    billingStore.openPaywall(route.fullPath, '定向备考')
    router.replace('/')
    return
  }
  if (!targetedStore.hasSelection) {
    router.replace('/targeted')
    return
  }
  if (!targetedStore.focusData) {
    targetedStore.fetchFocusAnalysis().catch(() => null)
  }
})

async function generateTargetedPractice() {
  if (isEmptyFocus.value) {
    message.warning(focusData.value?.emptyMessage || '暂无足够题库数据，请选择已有真实题库的考试方向后再练习。')
    return
  }
  await userStore.loadUserInfo().catch(() => null)
  if (!hasFullAccess.value) {
    billingStore.openPaywall(route.fullPath, '定向备考')
    router.replace('/')
    return
  }
  const questions = await targetedStore.fetchGeneratedQuestions(5)
  if (questions?.length) {
    message.success('题目已生成，请在下方核对后开始练习。')
  } else {
    message.warning('题库中暂无匹配题目，请返回调整考试方向。')
  }
}

function startTargetedPractice() {
  if (!targetedStore.generatedQuestions.length) {
    message.warning('请先生成针对性题目。')
    return
  }
  router.push({ path: '/exam/prepare', query: { source: 'targeted' } })
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

.generated-practice__header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
  margin-bottom: 14px;

  h3 {
    margin-bottom: 4px;
  }

  p {
    margin: 0;
    color: @text-secondary;
    font-size: @font-size-sm;
  }
}

.generated-practice__item {
  display: grid;
  grid-template-columns: 30px minmax(0, 1fr);
  gap: 10px;
  padding: 12px 0;
  border-top: 1px solid @divider-color;

  strong {
    width: 26px;
    height: 26px;
    display: inline-flex;
    align-items: center;
    justify-content: center;
    border-radius: 50%;
    background: @bg-light-blue;
    color: @primary-color;
  }

  span {
    color: @text-regular;
    line-height: 1.75;
  }
}

@media (max-width: 768px) {
  .generated-practice__header {
    align-items: stretch;
    flex-direction: column;
  }
}
</style>
