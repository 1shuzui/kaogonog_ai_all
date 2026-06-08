/**
 * 这个组合式函数封装 `useExamFlow` 相关浏览器行为；页面复用它，是为了少碰底层 API 和生命周期细节。
 *
 * @param 无；文件级模块依赖导出函数、组合式 API 或调用方传入上下文。
 * @return 导出可复用的端侧能力，具体返回值由各公共函数保持兼容。
 * @raises 不主动吞掉业务异常；请求失败、权限不足和运行时错误交由调用方或全局拦截器处理。
 */
import { ref, computed } from 'vue'
import { EXAM_STATUS } from '@/utils/constants'
import { useExamStore } from '@/stores/exam'

export function useExamFlow() {
  const examStore = useExamStore()

  const canStartPreparing = computed(() =>
    examStore.status === EXAM_STATUS.IDLE && examStore.currentQuestion
  )

  const canStartAnswering = computed(() =>
    examStore.status === EXAM_STATUS.PREPARING
  )

  const canSubmit = computed(() =>
    examStore.status === EXAM_STATUS.ANSWERING
  )

  const canGoNext = computed(() =>
    examStore.status === EXAM_STATUS.COMPLETED && !examStore.isLastQuestion
  )

  const isExamDone = computed(() =>
    examStore.status === EXAM_STATUS.COMPLETED && examStore.isLastQuestion
  )

  return {
    canStartPreparing,
    canStartAnswering,
    canSubmit,
    canGoNext,
    isExamDone
  }
}
