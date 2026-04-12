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
