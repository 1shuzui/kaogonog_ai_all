/**
 * 考试流程组合函数把考场状态机转成页面可读的按钮可用性，避免模板里散落状态判断。
 *
 * 它只解释当前状态下能否准备、作答、提交或进入下一题，不负责抽题、保存答案或评分，防止流程判断和业务动作耦合。
 *
 * @param 无；组合函数读取 exam store 的当前状态。
 * @return 导出准备、作答、提交、下一题和考试完成的布尔状态。
 * @raises 浏览器权限、网络和运行时异常按函数内部策略提示或交由调用方处理。
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
