/** Own suite loading and selection; discard stale responses and invalidate on disposal. */
import { computed, ref, watch, onScopeDispose } from 'vue'
import { getFullExamSuiteSummary } from '../utils/fullExamSuites.js'

export function useFullExamSelection({ targetFilterParams, hasFullAccess, loadSuites, onError = () => {} }) {
  const selectedFullExamSuiteId = ref('')
  const fullExamSuites = ref([])
  const fullExamSuitesLoading = ref(false)
  const fullExamSuitesError = ref('')
  const loadedFullExamScope = ref('')

  let fullExamSuitesRequest = 0

  const fullExamSuiteOptions = computed(() => fullExamSuites.value)

  const selectedFullExamSuite = computed(() => (
    fullExamSuiteOptions.value.find((suite) => suite.id === selectedFullExamSuiteId.value)
    || fullExamSuiteOptions.value[0]
    || null
  ))

  const selectedFullExamSuiteIndex = computed(() => Math.max(0, fullExamSuiteOptions.value.findIndex((suite) => suite.id === selectedFullExamSuite.value?.id)))

  const fullExamPickerOptions = computed(() => fullExamSuiteOptions.value.map((suite) => ({
    id: suite.id,
    label: suite.title
  })))

  const selectedFullExamSuiteLabel = computed(() => selectedFullExamSuite.value?.title || '暂无套题')

  const selectedFullExamSuiteSummary = computed(() => getFullExamSuiteSummary(selectedFullExamSuite.value))

  watch(fullExamSuiteOptions, (suites) => {
    if (!suites.length) {
      selectedFullExamSuiteId.value = ''
      return
    }
    if (!suites.some((suite) => suite.id === selectedFullExamSuiteId.value)) {
      selectedFullExamSuiteId.value = suites[0].id
    }
  }, { immediate: true })

  async function refreshFullExamSuites() {
    const request = ++fullExamSuitesRequest
    fullExamSuites.value = []
    selectedFullExamSuiteId.value = ''
    loadedFullExamScope.value = ''
    fullExamSuitesError.value = ''
    if (!hasFullAccess.value) {
      fullExamSuites.value = []
      selectedFullExamSuiteId.value = ''
      fullExamSuitesLoading.value = false
      return
    }
    fullExamSuitesLoading.value = true
    try {
      const filters = { ...targetFilterParams.value }
      const scopeKey = JSON.stringify(filters)
      const suites = await loadSuites(filters)
      if (request === fullExamSuitesRequest) {
        fullExamSuites.value = suites
        loadedFullExamScope.value = scopeKey
      }
    } catch (error) {
      if (request !== fullExamSuitesRequest) return
      fullExamSuites.value = []
      fullExamSuitesError.value = error?.message || '真题套卷加载失败，请稍后重试'
      onError(fullExamSuitesError.value)
    } finally {
      if (request === fullExamSuitesRequest) fullExamSuitesLoading.value = false
    }
  }

  function onFullExamSuiteChange(event) {
    const index = Number(event?.detail?.value || 0)
    const suite = fullExamSuiteOptions.value[index]
    if (suite) selectedFullExamSuiteId.value = suite.id
  }

  watch(targetFilterParams, () => {
    refreshFullExamSuites().catch(() => null)
  }, { deep: true, flush: 'sync' })

  function dispose() { fullExamSuitesRequest += 1 }
  onScopeDispose(dispose)

  return {
    fullExamSuites,
    fullExamSuitesLoading,
    fullExamSuitesError,
    loadedFullExamScope,
    fullExamSuiteOptions,
    selectedFullExamSuite,
    selectedFullExamSuiteIndex,
    fullExamPickerOptions,
    selectedFullExamSuiteLabel,
    selectedFullExamSuiteSummary,
    refreshFullExamSuites,
    onFullExamSuiteChange,
    dispose
  }
}
