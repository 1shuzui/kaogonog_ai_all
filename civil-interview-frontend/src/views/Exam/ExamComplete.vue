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
