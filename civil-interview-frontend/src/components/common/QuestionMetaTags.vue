<template>
  <div v-if="allTags.length || keywordTags.length" class="question-meta-tags" :class="{ 'is-emphasis': emphasis, 'is-compact': compact }">
    <div v-if="allTags.length" class="question-meta-tags__row">
      <span
        v-for="tag in allTags"
        :key="tag.key"
        class="question-meta-tags__chip"
        :class="`question-meta-tags__chip--${tag.tone}`"
      >
        {{ tag.label }}
      </span>
    </div>
    <div v-if="keywordTags.length" class="question-meta-tags__row question-meta-tags__row--keywords">
      <span
        v-for="keyword in keywordTags"
        :key="keyword"
        class="question-meta-tags__keyword"
      >
        {{ keyword }}
      </span>
    </div>
  </div>
</template>

<script setup>
import { computed } from 'vue'
import { buildQuestionHighlights } from '@/utils/questionPresentation'

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
  }
})

const highlight = computed(() => buildQuestionHighlights(props.question, { maxKeywords: props.maxKeywords }))
const allTags = computed(() => highlight.value.tags || [])
const keywordTags = computed(() => highlight.value.keywords || [])
</script>

<style lang="less" scoped>
@import '@/styles/variables.less';

.question-meta-tags {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.question-meta-tags__row {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.question-meta-tags__chip,
.question-meta-tags__keyword {
  display: inline-flex;
  align-items: center;
  min-height: 28px;
  padding: 0 10px;
  border-radius: 999px;
  font-size: 12px;
  line-height: 1;
}

.question-meta-tags__chip {
  border: 1px solid transparent;
  font-weight: 600;
}

.question-meta-tags__chip--type {
  color: #15477a;
  background: rgba(27, 95, 170, 0.1);
  border-color: rgba(27, 95, 170, 0.18);
}

.question-meta-tags__chip--province {
  color: #8a4d17;
  background: rgba(240, 169, 84, 0.14);
  border-color: rgba(212, 135, 25, 0.2);
}

.question-meta-tags__chip--source {
  color: #16625a;
  background: rgba(19, 194, 194, 0.12);
  border-color: rgba(19, 194, 194, 0.18);
}

.question-meta-tags__chip--reference {
  color: #5f2a8b;
  background: rgba(114, 46, 209, 0.12);
  border-color: rgba(114, 46, 209, 0.18);
}

.question-meta-tags__chip--warning {
  color: #8a2d16;
  background: rgba(255, 120, 72, 0.12);
  border-color: rgba(207, 72, 30, 0.18);
}

.question-meta-tags__keyword {
  color: @text-regular;
  background: rgba(255, 255, 255, 0.92);
  border: 1px dashed rgba(27, 95, 170, 0.22);
}

.is-emphasis .question-meta-tags__chip,
.is-emphasis .question-meta-tags__keyword {
  min-height: 30px;
  padding: 0 12px;
  box-shadow: 0 8px 16px rgba(24, 61, 107, 0.08);
}

.is-compact {
  gap: 6px;
}

.is-compact .question-meta-tags__chip,
.is-compact .question-meta-tags__keyword {
  min-height: 24px;
  padding: 0 8px;
  font-size: 11px;
}
</style>
