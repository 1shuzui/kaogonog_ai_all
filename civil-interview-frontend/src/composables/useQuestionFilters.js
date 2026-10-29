import { onBeforeUnmount, ref } from 'vue'
import { http } from '@/api'

export function useQuestionFilters() {
  const options = ref({ year: [], subcategory: [], subcategory2: [] })
  const loading = ref(false)
  const error = ref('')
  let sequence = 0
  let controller
  async function refresh(params = {}, enabled = true) {
    const id = ++sequence
    controller?.abort()
    error.value = ''
    options.value = { year: [], subcategory: [], subcategory2: [] }
    loading.value = enabled
    if (!enabled) return
    controller = new AbortController()
    try {
      const result = await http.get('/questions/filter-options', { params: { ...params, year: '' }, signal: controller.signal, skipErrorHandler: true })
      if (id !== sequence) return
      if (!result?.options || ['year', 'subcategory', 'subcategory2'].some(key => !Array.isArray(result.options[key]) || result.options[key].some(value => typeof value !== 'string'))) throw new Error('筛选选项格式异常，请重试')
      options.value = result.options
      return result.options
    } catch (cause) {
      if (id === sequence) error.value = cause.normalizedMessage || cause.message || '筛选选项暂时无法加载，请重试'
    } finally {
      if (id === sequence) { loading.value = false; controller = null }
    }
  }
  onBeforeUnmount(() => { sequence++; controller?.abort() })
  return { options, loading, error, refresh }
}
