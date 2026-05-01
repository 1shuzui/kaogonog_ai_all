<template>
  <div class="question-rich-content" :class="{ 'is-dark': dark, 'is-compact': compact }">
    <div v-if="isComic || isLong" class="question-rich-content__flags">
      <span v-if="isComic" class="question-rich-content__flag question-rich-content__flag--comic">漫画题 / 材料题</span>
      <span v-if="isLong" class="question-rich-content__flag question-rich-content__flag--long">长题干</span>
    </div>

    <div
      class="question-rich-content__body"
      :class="{
        'is-collapsed': expandable && !expanded,
        'is-scrollable': scrollable
      }"
      :style="bodyStyle"
    >
      <p
        v-for="(paragraph, index) in paragraphs"
        :key="`${index}-${paragraph}`"
        class="question-rich-content__paragraph"
      >
        {{ paragraph }}
      </p>
    </div>

    <button
      v-if="expandable"
      type="button"
      class="question-rich-content__toggle"
      @click.stop="expanded = !expanded"
    >
      {{ expanded ? '收起题目' : '展开题目' }}
    </button>
  </div>
</template>

<script setup>
import { computed, ref, watch } from 'vue'
import { isComicQuestion, isLongQuestion, splitQuestionContent } from '@/utils/questionPresentation'

const props = defineProps({
  text: {
    type: String,
    default: ''
  },
  dark: {
    type: Boolean,
    default: false
  },
  compact: {
    type: Boolean,
    default: false
  },
  scrollable: {
    type: Boolean,
    default: false
  },
  initialExpanded: {
    type: Boolean,
    default: false
  },
  collapsedHeight: {
    type: Number,
    default: 160
  },
  scrollHeight: {
    type: Number,
    default: 320
  }
})

const expanded = ref(props.initialExpanded)

watch(
  () => props.text,
  () => {
    expanded.value = props.initialExpanded
  }
)

const paragraphs = computed(() => splitQuestionContent(props.text))
const isComic = computed(() => isComicQuestion(props.text))
const isLong = computed(() => isLongQuestion(props.text))
const expandable = computed(() => paragraphs.value.length > 3 || String(props.text || '').length > 120)
const bodyStyle = computed(() => {
  if (props.scrollable) {
    return {
      maxHeight: `${props.scrollHeight}px`
    }
  }

  if (expandable.value && !expanded.value) {
    return {
      maxHeight: `${props.collapsedHeight}px`
    }
  }

  return {}
})
</script>

<style lang="less" scoped>
@import '@/styles/variables.less';

.question-rich-content {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.question-rich-content__flags {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.question-rich-content__flag {
  display: inline-flex;
  align-items: center;
  min-height: 26px;
  padding: 0 10px;
  border-radius: 999px;
  font-size: 12px;
  font-weight: 600;
}

.question-rich-content__flag--comic {
  color: #7a3b12;
  background: rgba(255, 196, 87, 0.18);
}

.question-rich-content__flag--long {
  color: #185699;
  background: rgba(27, 95, 170, 0.12);
}

.question-rich-content__body {
  position: relative;
  overflow: hidden;
}

.question-rich-content__body.is-collapsed::after {
  content: '';
  position: absolute;
  left: 0;
  right: 0;
  bottom: 0;
  height: 44px;
  background: linear-gradient(180deg, rgba(255, 255, 255, 0) 0%, rgba(255, 255, 255, 0.96) 100%);
  pointer-events: none;
}

.question-rich-content__body.is-scrollable {
  overflow-y: auto;
  padding-right: 4px;
}

.question-rich-content__body.is-scrollable::after {
  display: none;
}

.question-rich-content__paragraph {
  margin: 0;
  white-space: pre-wrap;
  word-break: break-word;
  line-height: 1.9;
}

.question-rich-content__toggle {
  align-self: flex-start;
  padding: 0;
  border: 0;
  background: transparent;
  color: @primary-color;
  font-size: 13px;
  font-weight: 600;
  cursor: pointer;
}

.is-dark .question-rich-content__body.is-collapsed::after {
  background: linear-gradient(180deg, rgba(43, 48, 58, 0) 0%, rgba(43, 48, 58, 0.95) 100%);
}

.is-dark .question-rich-content__paragraph {
  color: rgba(255, 255, 255, 0.92);
}

.is-dark .question-rich-content__toggle {
  color: #9ec8ff;
}

.is-compact {
  gap: 8px;
}

.is-compact .question-rich-content__paragraph {
  font-size: 14px;
  line-height: 1.75;
}

.is-compact .question-rich-content__flag {
  min-height: 22px;
  padding: 0 8px;
  font-size: 11px;
}
</style>
