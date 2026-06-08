<!--
这个组件展示扣分原因和可改进点，帮助用户知道分数丢在哪里，而不只是看到总分。

@param: 无；页面运行时从 props、路由参数、Pinia 状态和用户点击中拿数据。
@return: 渲染当前业务界面，并把按钮、表单或跳转事件交给既有流程处理。
@raises: 不主动抛业务异常；接口失败、未登录和权限不足由请求层或页面提示承接。
-->
<template>
  <div class="loss-analysis" :class="{ 'loss-analysis--compact': compact }">
    <h4 class="loss-analysis__title">失分诊断</h4>
    <div class="loss-analysis__list">
      <div v-for="dim in dimensions" :key="dim.name" class="loss-analysis__item">
        <DimensionBar
          :name="dim.name"
          :score="dim.score"
          :maxScore="dim.maxScore"
          :compact="compact"
        />
        <div class="loss-analysis__reasons" v-if="dim.lostReasons?.length">
          <span v-for="(reason, i) in dim.lostReasons" :key="i" class="loss-reason">
            {{ reason }}
          </span>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import DimensionBar from './DimensionBar.vue'

defineProps({
  dimensions: { type: Array, default: () => [] },
  compact: { type: Boolean, default: false }
})
</script>

<style lang="less" scoped>
@import '@/styles/variables.less';

.loss-analysis {
  background: @card-bg;
  border-radius: @border-radius-lg;
  padding: 16px;
}

.loss-analysis__title {
  font-size: @font-size-lg;
  color: @text-primary;
  margin-bottom: 16px;
}

.loss-analysis__item {
  margin-bottom: 16px;
  &:last-child { margin-bottom: 0; }
}

.loss-analysis__reasons {
  margin-top: 4px;
  padding-left: 4px;
}

.loss-reason {
  display: inline-block;
  font-size: @font-size-xs;
  color: @score-red;
  background: fade(@score-red, 8%);
  padding: 2px 8px;
  border-radius: 10px;
  margin-right: 6px;
  margin-top: 4px;
}

.loss-analysis--compact {
  padding: 14px;

  .loss-analysis__title {
    font-size: @font-size-base;
    margin-bottom: 12px;
  }

  .loss-analysis__item {
    margin-bottom: 12px;
  }

  .loss-analysis__reasons {
    margin-top: 2px;
  }

  .loss-reason {
    font-size: 11px;
    padding: 1px 7px;
    border-radius: 999px;
  }
}
</style>
