<template>
  <div class="transcript-viewer">
    <h4 class="transcript-viewer__title">{{ title }}</h4>
    <div class="transcript-viewer__content" v-html="highlightedContent"></div>
  </div>
</template>

<script setup>
import { computed } from 'vue'

const props = defineProps({
  title: { type: String, default: '答题文字稿' },
  transcript: { type: String, default: '' },
  keywords: {
    type: Object,
    default: () => ({ scoring: [], deducting: [], bonus: [] })
  },
  highlightedHtml: { type: String, default: '' }
})

const highlightedContent = computed(() => {
  if (props.highlightedHtml) return props.highlightedHtml

  let text = escapeHtml(props.transcript)

  // 按关键词长度降序排列，优先匹配长词
  const allKeywords = [
    ...(props.keywords.scoring || []).map(k => ({ word: k.word || k, cls: 'kw-scoring' })),
    ...(props.keywords.deducting || []).map(k => ({ word: k.word || k, cls: 'kw-deducting' })),
    ...(props.keywords.bonus || []).map(k => ({ word: k.word || k, cls: 'kw-bonus' }))
  ].sort((a, b) => b.word.length - a.word.length)

  for (const kw of allKeywords) {
    const escaped = kw.word.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')
    const regex = new RegExp(escaped, 'g')
    text = text.replace(regex, `<span class="${kw.cls}">${kw.word}</span>`)
  }

  // 段落换行
  text = text.replace(/\n\n/g, '</p><p>').replace(/\n/g, '<br>')
  return `<p>${text}</p>`
})

function escapeHtml(str) {
  const div = document.createElement('div')
  div.textContent = str
  return div.innerHTML
}
</script>

<style lang="less" scoped>
@import '@/styles/variables.less';

.transcript-viewer {
  background: @card-bg;
  border-radius: @border-radius-lg;
  padding: 16px;
}

.transcript-viewer__title {
  font-size: @font-size-lg;
  color: @text-primary;
  margin-bottom: 12px;
}

.transcript-viewer__content {
  font-size: @font-size-base;
  color: @text-regular;
  line-height: 1.8;

  :deep(.kw-scoring) {
    background: fade(@score-green, 15%);
    color: @score-green;
    padding: 1px 4px;
    border-radius: 3px;
    font-weight: 500;
  }
  :deep(.kw-deducting) {
    background: fade(@score-red, 15%);
    color: @score-red;
    padding: 1px 4px;
    border-radius: 3px;
    font-weight: 500;
  }
  :deep(.kw-bonus) {
    background: fade(@score-gold, 15%);
    color: @score-gold;
    padding: 1px 4px;
    border-radius: 3px;
    font-weight: 500;
  }
}
</style>
