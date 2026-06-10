<!--
PC 考场页的分发壳，根据考试来源选择全真模拟考场或普通练习考场组件。

这里不直接写录音、计时和提交逻辑，是为了让全真模拟和专项练习各自保留不同的题本体验。
共同边界是：作答前只显示题干、题号、计时和媒体控制，不显示评分分数或评分后才该出现的反馈。

@param: 无；考试来源和模式来自 exam store。
@return: 渲染 FullExamRoom 或 StandardExamRoom。
@raises: 不主动抛业务异常；具体考场组件负责处理媒体权限、接口失败和提交错误。
-->
<template>
  <FullExamRoom v-if="examStore.fullExamMode" />
  <StandardExamRoom v-else />
</template>

<script setup>
import { useExamStore } from '@/stores/exam'
import FullExamRoom from '@/components/exam/FullExamRoom.vue'
import StandardExamRoom from '@/components/exam/StandardExamRoom.vue'

const examStore = useExamStore()
</script>
