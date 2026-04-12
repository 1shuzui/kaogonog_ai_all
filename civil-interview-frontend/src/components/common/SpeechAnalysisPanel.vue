<template>
  <div class="speech-panel card" v-if="analysis && analysis.fluencyScore > 0">
    <h3><SoundOutlined /> 普通话与表达分析</h3>

    <!-- 流畅度评分 -->
    <div class="speech-score">
      <div class="speech-score__ring">
        <ScoreRing :score="analysis.fluencyScore" :maxScore="100" size="small" :label="analysis.fluencyLevel" />
      </div>
      <div class="speech-score__metrics">
        <div class="metric">
          <span class="metric__label">语速</span>
          <span class="metric__value">{{ analysis.speechRate }} 字/分</span>
          <a-tag :color="rateColor" size="small">{{ analysis.speechRateLevel }}</a-tag>
        </div>
        <div class="metric">
          <span class="metric__label">口头禅</span>
          <span class="metric__value">{{ analysis.fillerCount }} 次</span>
          <a-tag :color="fillerColor" size="small">{{ fillerLabel }}</a-tag>
        </div>
        <div class="metric">
          <span class="metric__label">规范用语</span>
          <span class="metric__value">{{ analysis.formalPhrases.length }} 个</span>
        </div>
      </div>
    </div>

    <!-- 口头禅详情 -->
    <div v-if="analysis.fillerDetails.length" class="speech-detail">
      <h4>口头禅分布</h4>
      <div class="filler-tags">
        <span v-for="f in analysis.fillerDetails" :key="f.word" class="filler-tag">
          {{ f.word }} <strong>×{{ f.count }}</strong>
        </span>
      </div>
    </div>

    <!-- 规范用语 -->
    <div v-if="analysis.formalPhrases.length" class="speech-detail">
      <h4>使用的规范用语</h4>
      <div class="formal-tags">
        <a-tag v-for="phrase in analysis.formalPhrases" :key="phrase" color="green">{{ phrase }}</a-tag>
      </div>
    </div>

    <!-- 改进建议 -->
    <div class="speech-detail">
      <h4>改进建议</h4>
      <div v-for="(s, idx) in analysis.suggestions" :key="idx" class="suggestion-item">
        <BulbOutlined style="color: #D48806; margin-right: 6px" />
        <span>{{ s }}</span>
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed } from 'vue'
import { SoundOutlined, BulbOutlined } from '@ant-design/icons-vue'
import ScoreRing from '@/components/common/ScoreRing.vue'

const props = defineProps({
  analysis: {
    type: Object,
    default: null
  }
})

const rateColor = computed(() => {
  if (!props.analysis) return 'default'
  if (props.analysis.speechRateLevel === '适中') return 'green'
  return 'orange'
})

const fillerColor = computed(() => {
  if (!props.analysis) return 'default'
  if (props.analysis.fillerCount <= 2) return 'green'
  if (props.analysis.fillerCount <= 5) return 'orange'
  return 'red'
})

const fillerLabel = computed(() => {
  if (!props.analysis) return ''
  if (props.analysis.fillerCount <= 2) return '较少'
  if (props.analysis.fillerCount <= 5) return '适中'
  return '较多'
})
</script>

<style lang="less" scoped>
@import '@/styles/variables.less';

.speech-panel {
  padding: 16px;
  margin-bottom: 12px;

  h3 {
    font-size: @font-size-lg;
    color: @text-primary;
    margin-bottom: 16px;
    display: flex;
    align-items: center;
    gap: 6px;
  }
}

.speech-score {
  display: flex;
  align-items: center;
  gap: 20px;
  margin-bottom: 16px;
}

.speech-score__metrics {
  flex: 1;
}

.metric {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 8px;

  &:last-child {
    margin-bottom: 0;
  }
}

.metric__label {
  font-size: @font-size-sm;
  color: @text-secondary;
  min-width: 56px;
}

.metric__value {
  font-size: @font-size-base;
  color: @text-regular;
  font-weight: 500;
}

.speech-detail {
  margin-top: 14px;
  padding-top: 14px;
  border-top: 1px solid @divider-color;

  h4 {
    font-size: @font-size-base;
    color: @text-primary;
    margin-bottom: 10px;
  }
}

.filler-tags {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.filler-tag {
  padding: 4px 10px;
  border-radius: 12px;
  background: #FFF7E6;
  color: #D48806;
  font-size: @font-size-sm;

  strong {
    color: #CF1322;
    margin-left: 2px;
  }
}

.formal-tags {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
}

.suggestion-item {
  display: flex;
  align-items: flex-start;
  margin-bottom: 8px;
  font-size: @font-size-sm;
  color: @text-regular;
  line-height: 1.5;

  &:last-child {
    margin-bottom: 0;
  }
}
</style>
