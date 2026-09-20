<!--
小程序专项训练首页只展示训练分类入口，训练分类用于题型练习，不等同于评分里的能力维度。
移动端从这里进入具体题型后再生成题目，避免首页提前消耗权益或请求受保护题库。

@param: 无；页面读取训练分类常量和本地训练进度摘要。
@return: 渲染题型入口列表和进入单项训练页的跳转。
@raises: 不主动抛业务异常；接口失败、未登录和权限不足由请求层或页面提示承接。
-->
<template>
  <view class="motion-page page page--tab training-page" :class="motionClass" :style="motionStyle">
    <view class="motion-page-heading">
      <view>
        <text class="motion-eyebrow">集中练习 · 逐项提升</text>
        <text class="page-title">专项训练</text>
      </view>
      <view class="motion-heading-icon">
        <MotionAccent :active="visible"><LearnerIcon name="aim" :size="32" /></MotionAccent>
      </view>
    </view>
    <text class="page-desc">按题型集中训练，逐个突破短板。</text>

    <view class="training-list">
      <button
        v-for="category in TRAINING_CATEGORIES"
        :key="category.key"
        class="training-card card"
        :aria-label="`${category.name}，${category.tip} ${progressText(category.key)}，进入训练`"
        @tap="openDimension(category)"
      >
        <view class="training-card__icon">
          <LearnerIcon :name="TRAINING_ICONS[category.key] || 'read'" :size="28" />
        </view>
        <view class="training-card__copy">
          <text class="training-card__title">{{ category.name }}</text>
          <text class="training-card__desc">{{ category.tip }}</text>
          <text class="training-card__meta">{{ progressText(category.key) }}</text>
        </view>
        <LearnerIcon name="arrow-right" :size="18" />
      </button>
    </view>
  </view>
</template>

<script setup>
import LearnerIcon from '../../components/LearnerIcon.vue'
import MotionAccent from '../../components/MotionAccent.vue'
import { usePageMotion } from '../../motion/useMotion'
const { motionClass, motionStyle, visible } = usePageMotion()
import { useTrainingStore } from '../../stores/training'
import { TRAINING_CATEGORIES } from '../../utils/constants'

const trainingStore = useTrainingStore()
// View-only mapping: shared question categories and request dimensions stay intact.
const TRAINING_ICONS = {
  analysis: 'read',
  organization: 'solution',
  emergency: 'field-time',
  interpersonal: 'sound',
  simulation: 'audio',
  career: 'aim'
}

function progressText(key) {
  const progress = trainingStore.getDimensionProgress(key)
  if (!progress.attempts) return '尚未练习'
  return `练习 ${progress.attempts} 次 · 最佳 ${progress.bestScore} 分`
}

function openDimension(category) {
  uni.navigateTo({ url: `/pages/training/dimension?key=${encodeURIComponent(category.key)}` })
}
</script>

<style scoped>
.training-page {
  color: var(--ui-text, #203047);
  background: var(--ui-bg, #f7f9fd);
}

.training-page .page-title {
  color: var(--ui-text, #203047);
  font-size: 24px;
}

.training-page .motion-eyebrow {
  color: var(--ui-muted, #596a80);
  font-size: 14px;
  letter-spacing: 0;
}

.training-page .page-desc {
  color: var(--ui-muted, #596a80);
  font-size: 14px;
  line-height: 1.7;
}

.training-page .motion-heading-icon {
  background: var(--ui-soft, #edf3ff);
  border-color: var(--ui-border, #dbe3ee);
}

.training-list {
  display: grid;
  gap: 12px;
}

.training-page .training-card {
  display: grid;
  grid-template-columns: 44px minmax(0, 1fr) 18px;
  gap: 12px;
  align-items: center;
  width: 100%;
  min-height: 44px;
  margin: 0;
  padding: 16px;
  box-sizing: border-box;
  text-align: left;
  white-space: normal;
  color: var(--ui-text, #203047);
  background: var(--ui-surface, #fdfefe);
  border: 1px solid var(--ui-border, #dbe3ee);
  border-radius: 12px;
  box-shadow: none;
}

.training-card:focus-visible {
  outline: 2px solid var(--ui-primary, #326be5);
  outline-offset: 3px;
}

.training-page .training-card__icon {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 44px;
  height: 44px;
  border-radius: 12px;
  background: var(--ui-soft, #edf3ff);
}

.training-card__copy {
  min-width: 0;
  overflow-wrap: anywhere;
}

.training-card__title,
.training-card__desc,
.training-card__meta {
  display: block;
}

.training-card__title {
  color: var(--ui-text, #203047);
  font-size: 16px;
  font-weight: 700;
  line-height: 1.5;
}

.training-card__desc {
  margin-top: 4px;
  color: var(--ui-muted, #596a80);
  font-size: 14px;
  line-height: 1.7;
}

.training-card__meta {
  margin-top: 8px;
  color: var(--ui-link, #285bc7);
  font-size: 14px;
  line-height: 1.5;
}
</style>
