<!--
这个网页完成页承接考试提交后的过渡状态，负责把用户引导到成绩结果或历史复盘。

@param: 无；页面运行时从 props、路由参数、Pinia 状态和用户点击中拿数据。
@return: 渲染当前业务界面，并把按钮、表单或跳转事件交给既有流程处理。
@raises: 不主动抛业务异常；接口失败、未登录和权限不足由请求层或页面提示承接。
-->
<template>
  <div class="exam-complete page-container">
    <div class="exam-complete__card card">
      <CheckCircleFilled class="exam-complete__icon" />
      <h2>答题完成</h2>
      <p>共完成 {{ examStore.totalQuestions }} 道题目</p>
      <p class="exam-complete__hint">系统正在生成评测报告...</p>
      <a-progress :percent="progress" :status="progress < 100 ? 'active' : 'success'" />
      <a-button
        type="primary"
        size="large"
        block
        :disabled="progress < 100"
        @click="viewResult"
        style="margin-top: 24px"
      >
        查看测评结果
      </a-button>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { CheckCircleFilled } from '@ant-design/icons-vue'
import { useExamStore } from '@/stores/exam'

const router = useRouter()
const route = useRoute()
const examStore = useExamStore()
const progress = ref(0)

onMounted(() => {
  const timer = setInterval(() => {
    progress.value = Math.min(progress.value + 10, 100)
    if (progress.value >= 100) clearInterval(timer)
  }, 300)
})

function viewResult() {
  router.push(`/result/${route.params.examId}`)
}
</script>

<style lang="less" scoped>
@import '@/styles/variables.less';

.exam-complete {
  display: flex;
  align-items: center;
  justify-content: center;
  min-height: calc(100vh - @header-height);
}

.exam-complete__card {
  text-align: center;
  padding: 40px 24px;
  max-width: 400px;
  width: 100%;

  h2 {
    font-size: @font-size-xxl;
    color: @text-primary;
    margin: 16px 0 8px;
  }
  p {
    color: @text-secondary;
    margin-bottom: 8px;
  }
}

.exam-complete__icon {
  font-size: 64px;
  color: @score-green;
}

.exam-complete__hint {
  margin-bottom: 16px;
}
</style>
