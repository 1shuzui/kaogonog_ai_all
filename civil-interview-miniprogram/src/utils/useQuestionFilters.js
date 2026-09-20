import { onBeforeUnmount, ref } from 'vue'
import { getQuestionFilterOptions } from '../api/questionFilters'
import { createCancellation } from './cancellation.mjs'

// Page-local metadata, never a cross-account cache. Each request owns its cleanup.
export function useQuestionFilters() {
  const options = ref({ year: [], subcategory: [], subcategory2: [] })
  const loading = ref(false)
  const error = ref('')
  const questionCount = ref(0)
  let sequence = 0
  let active = null
  async function refresh(params = {}, enabled = true) {
    const id = ++sequence
    active?.cancel()
    active = null
    error.value = ''
    options.value = { year: [], subcategory: [], subcategory2: [] }
    questionCount.value = 0
    loading.value = enabled
    if (!enabled) return
    const cancellation = createCancellation()
    active = cancellation
    try {
      const response = await getQuestionFilterOptions({ ...params, year: '' }, { signal: cancellation.signal })
      if (id !== sequence) return
      options.value = response.options
      questionCount.value = response.questionCount || 0
    } catch (cause) {
      if (id === sequence) error.value = cause?.message || '筛选选项暂时无法加载，请重试'
    } finally {
      if (id === sequence) { loading.value = false; active = null }
    }
  }
  onBeforeUnmount(() => { sequence += 1; active?.cancel(); active = null })
  return { options, loading, error, questionCount, refresh }
}
