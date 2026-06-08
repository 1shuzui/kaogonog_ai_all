<!--
这个网页考场页承载录音录像、计时和提交，答题前只展示题干和进度，不展示评分分数。

@param: 无；页面运行时从 props、路由参数、Pinia 状态和用户点击中拿数据。
@return: 渲染当前业务界面，并把按钮、表单或跳转事件交给既有流程处理。
@raises: 不主动抛业务异常；接口失败、未登录和权限不足由请求层或页面提示承接。
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
