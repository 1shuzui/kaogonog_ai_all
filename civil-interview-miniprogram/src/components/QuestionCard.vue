<template>
  <view
    class="question-card card"
    :class="{ 'question-card--emphasis': emphasis, 'question-card--compact': compact }"
    @tap="emit('select', question)"
  >
    <!-- MetaTags row -->
    <view v-if="showMetaTags" class="question-card__meta">
      <view class="question-card__tags">
        <text
          v-for="tag in highlightTags"
          :key="tag.key"
          class="question-card__tag"
          :class="`question-card__tag--${tag.tone}`"
        >{{ tag.label }}</text>
      </view>
      <text class="question-card__points">{{ pointsCount }} 个采分点</text>
    </view>

    <!-- Legacy top row (backward compat when showMetaTags is false) -->
    <view v-else class="question-card__top">
      <view class="question-card__tags">
        <text class="question-card__tag">{{ provinceName }}</text>
        <text class="question-card__tag question-card__tag--blue">{{ categoryName }}</text>
        <text v-if="isProvinceFallback" class="question-card__tag question-card__tag--warning">国考补充</text>
      </view>
      <text class="question-card__points">{{ pointsCount }} 个采分点</text>
    </view>

    <!-- RichContent stem -->
    <view v-if="showRichContent" class="question-card__rich-stem">
      <!-- Comic/long question flags -->
      <view v-if="comicFlag || longFlag" class="question-card__flags">
        <text v-if="comicFlag" class="question-card__flag question-card__flag--comic">漫画题</text>
        <text v-if="longFlag" class="question-card__flag question-card__flag--long">长题干</text>
      </view>

      <!-- Paragraph body -->
      <view
        :class="[
          'question-card__body',
          { 'question-card__body--collapsed': !expanded && hasOverflow }
        ]"
        :style="collapsedStyle"
      >
        <text
          v-for="(para, idx) in paragraphs"
          :key="idx"
          class="question-card__para"
        >{{ para }}</text>
      </view>

      <!-- Expand/collapse toggle -->
      <view v-if="hasOverflow && showExpandToggle" class="question-card__toggle" @tap.stop="expanded = !expanded">
        <text class="question-card__toggle-text">{{ expanded ? '收起' : '展开全文' }}</text>
        <text class="question-card__toggle-icon">{{ expanded ? '▲' : '▼' }}</text>
      </view>
    </view>

    <!-- Legacy stem (4-line clamp, backward compat) -->
    <text v-else class="question-card__stem">{{ question?.stem || '暂无题干' }}</text>

    <!-- Keywords row -->
    <view v-if="displayKeywords.length" class="question-card__keywords">
      <text
        v-for="keyword in displayKeywords"
        :key="keyword"
        class="question-card__keyword"
        :class="{ 'question-card__keyword--dashed': showMetaTags }"
      >{{ keyword }}</text>
    </view>
  </view>
</template>

<script setup>
import { computed, ref } from 'vue'
import { getCategoryName, getProvinceName } from '../utils/constants'
import {
  isComicQuestion,
  isLongQuestion,
  splitQuestionContent,
  buildQuestionHighlights
} from '../utils/questionPresentation'

const props = defineProps({
  question: {
    type: Object,
    default: () => ({})
  },
  emphasis: {
    type: Boolean,
    default: false
  },
  compact: {
    type: Boolean,
    default: false
  },
  maxKeywords: {
    type: Number,
    default: 4
  },
  showRichContent: {
    type: Boolean,
    default: false
  },
  showMetaTags: {
    type: Boolean,
    default: false
  },
  scrollable: {
    type: Boolean,
    default: false
  },
  collapsedHeight: {
    type: Number,
    default: 320
  },
  showExpandToggle: {
    type: Boolean,
    default: true
  }
})

const emit = defineEmits(['select'])

const expanded = ref(false)

const isProvinceFallback = computed(() => !!props.question?.isProvinceFallback)
const provinceName = computed(() => {
  const code = isProvinceFallback.value && props.question?.requestedProvince
    ? props.question.requestedProvince
    : (props.question?.province || 'national')
  return getProvinceName(code)
})
const categoryName = computed(() => getCategoryName(props.question?.dimension || props.question?.type || ''))
const pointsCount = computed(() => Array.isArray(props.question?.scoringPoints) ? props.question.scoringPoints.length : 0)

// --- RichContent computed ---
const stemText = computed(() => props.question?.stem || '')
const comicFlag = computed(() => isComicQuestion(stemText.value))
const longFlag = computed(() => isLongQuestion(stemText.value))
const paragraphs = computed(() => {
  const parts = splitQuestionContent(stemText.value)
  return parts.length ? parts : [stemText.value || '暂无题干']
})
const hasOverflow = computed(() => {
  if (props.scrollable) return false
  return stemText.value.length > 120 || paragraphs.value.length >= 3
})
const collapsedStyle = computed(() => {
  if (!hasOverflow.value || expanded.value || props.scrollable) return {}
  return { maxHeight: `${props.collapsedHeight}rpx`, overflow: 'hidden' }
})

// --- MetaTags computed ---
const highlights = computed(() => {
  if (!props.showMetaTags) return { tags: [], keywords: [] }
  return buildQuestionHighlights(props.question, { maxKeywords: props.maxKeywords })
})
const highlightTags = computed(() => highlights.value.tags)

const displayKeywords = computed(() => {
  if (props.showMetaTags) {
    return highlights.value.keywords.slice(0, props.maxKeywords)
  }
  const source = props.question?.keywords
  if (Array.isArray(source)) return source.slice(0, 4)
  if (source?.scoring) return source.scoring.slice(0, 4)
  return []
})
</script>

<style scoped>
.question-card {
  position: relative;
}

.question-card--emphasis {
  padding: 28rpx 24rpx;
  box-shadow: 0 2rpx 16rpx rgba(0, 0, 0, 0.06);
}

.question-card--compact {
  padding: 18rpx 20rpx;
}

/* Legacy top row */
.question-card__top {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 16rpx;
  margin-bottom: 16rpx;
}

.question-card__tags {
  display: flex;
  flex-wrap: wrap;
  gap: 10rpx;
}

.question-card__tag {
  padding: 6rpx 14rpx;
  border-radius: 999rpx;
  background: #eef4ff;
  color: #45617e;
  font-size: 22rpx;
}

.question-card__tag--blue,
.question-card__tag--type {
  background: #e8f4fd;
  color: #1b5faa;
}

.question-card__tag--warning {
  background: #fff2e8;
  color: #cf6d20;
}

.question-card__tag--province {
  background: #fef7e8;
  color: #8c6d1f;
}

.question-card__tag--source {
  background: #e8faf0;
  color: #1f7a4a;
}

.question-card__tag--reference {
  background: #f5f0ff;
  color: #5b2fa8;
}

.question-card__points {
  flex-shrink: 0;
  color: #6f7c8f;
  font-size: 22rpx;
}

/* MetaTags row */
.question-card__meta {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 16rpx;
  margin-bottom: 16rpx;
}

/* Legacy stem */
.question-card__stem {
  display: -webkit-box;
  overflow: hidden;
  color: #1f2b3d;
  font-size: 29rpx;
  line-height: 1.7;
  -webkit-box-orient: vertical;
  -webkit-line-clamp: 4;
}

/* Rich stem */
.question-card__rich-stem {
  position: relative;
}

.question-card__flags {
  display: flex;
  gap: 10rpx;
  margin-bottom: 12rpx;
}

.question-card__flag {
  padding: 4rpx 12rpx;
  border-radius: 6rpx;
  font-size: 20rpx;
}

.question-card__flag--comic {
  background: #ffeaea;
  color: #c53030;
}

.question-card__flag--long {
  background: #fff3e0;
  color: #b85c00;
}

.question-card__body {
  overflow: hidden;
  transition: max-height 0.25s ease;
}

.question-card__body--collapsed {
  position: relative;
}

.question-card__body--collapsed::after {
  content: '';
  position: absolute;
  bottom: 0;
  left: 0;
  right: 0;
  height: 60rpx;
  background: linear-gradient(transparent, #ffffff);
}

.question-card__para {
  display: block;
  color: #1f2b3d;
  font-size: 29rpx;
  line-height: 1.7;
  margin-bottom: 12rpx;
}

.question-card__toggle {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 8rpx;
  padding: 16rpx 0 4rpx;
}

.question-card__toggle-text {
  color: #1b5faa;
  font-size: 26rpx;
}

.question-card__toggle-icon {
  color: #1b5faa;
  font-size: 20rpx;
}

/* Keywords */
.question-card__keywords {
  display: flex;
  flex-wrap: wrap;
  gap: 10rpx;
  margin-top: 18rpx;
}

.question-card__keyword {
  padding: 6rpx 12rpx;
  border-radius: 8rpx;
  background: #f6f8fb;
  color: #6f7c8f;
  font-size: 22rpx;
}

.question-card__keyword--dashed {
  background: transparent;
  border: 1rpx dashed #d0d7e3;
  color: #5a6b82;
}
</style>
