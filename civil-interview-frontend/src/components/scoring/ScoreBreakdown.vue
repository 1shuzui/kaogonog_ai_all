<template>
  <div class="score-breakdown">
    <h4 class="score-breakdown__title">评分关键词分析</h4>

    <div class="score-breakdown__group" v-if="keywords.scoring?.length">
      <div class="score-breakdown__label">
        <CheckCircleFilled style="color: #389E0D" /> 得分关键词
      </div>
      <div class="score-breakdown__tags">
        <KeywordTag
          v-for="kw in keywords.scoring"
          :key="kw.word"
          :word="kw.word"
          type="scoring"
          :value="kw.score"
          :matched="kw.inTranscript"
        />
      </div>
    </div>

    <div class="score-breakdown__group" v-if="keywords.deducting?.length">
      <div class="score-breakdown__label">
        <CloseCircleFilled style="color: #CF1322" /> 扣分关键词
      </div>
      <div class="score-breakdown__tags">
        <KeywordTag
          v-for="kw in keywords.deducting"
          :key="kw.word"
          :word="kw.word"
          type="deducting"
          :value="kw.penalty"
          :matched="kw.inTranscript"
        />
      </div>
    </div>

    <div class="score-breakdown__group" v-if="keywords.bonus?.length">
      <div class="score-breakdown__label">
        <StarFilled style="color: #D48806" /> 加分关键词
      </div>
      <div class="score-breakdown__tags">
        <KeywordTag
          v-for="kw in keywords.bonus"
          :key="kw.word"
          :word="kw.word"
          type="bonus"
          :value="kw.bonus"
          :matched="kw.inTranscript"
        />
      </div>
    </div>
  </div>
</template>

<script setup>
import { CheckCircleFilled, CloseCircleFilled, StarFilled } from '@ant-design/icons-vue'
import KeywordTag from '@/components/common/KeywordTag.vue'

defineProps({
  keywords: {
    type: Object,
    default: () => ({ scoring: [], deducting: [], bonus: [] })
  }
})
</script>

<style lang="less" scoped>
@import '@/styles/variables.less';

.score-breakdown {
  background: @card-bg;
  border-radius: @border-radius-lg;
  padding: 16px;
}

.score-breakdown__title {
  font-size: @font-size-lg;
  color: @text-primary;
  margin-bottom: 16px;
}

.score-breakdown__group {
  margin-bottom: 16px;

  &:last-child {
    margin-bottom: 0;
  }
}

.score-breakdown__label {
  font-size: @font-size-sm;
  color: @text-secondary;
  margin-bottom: 8px;
  display: flex;
  align-items: center;
  gap: 6px;
}

.score-breakdown__tags {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}
</style>
