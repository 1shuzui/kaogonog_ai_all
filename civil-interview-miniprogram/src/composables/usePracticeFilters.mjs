/** Own practice scope and type selection; metadata uses the same effective query as Start. */
import { computed, ref, watch } from 'vue'
import { QUESTION_CATEGORIES } from '../utils/constants.js'
import { DEFAULT_TARGETED_POSITION_TREE } from '../utils/targetedOptions.js'
import { normalizeProvinceCode } from '../utils/fullExamSuites.js'

export const RANDOM_DIMENSION_KEY = 'random'

export function usePracticeFilters({ userStore, selection, fixedPracticeEntry, mode, hasFullAccess, filterMetadata }) {
  const selectedDimensions = ref(['random'])
  const questionTypeTouched = ref(false)
  const selectedExamCategoryId = ref('')
  const selectedRegionId = ref('')
  const selectedDirectionId = ref('')
  const selectedYearsFilter = ref([])
  const targetFilterTouched = ref(false)

  const questionCategoryOptions = [
    { key: RANDOM_DIMENSION_KEY, name: '随机题型' },
    ...QUESTION_CATEGORIES.filter((item) => item.key)
  ]

  const showPracticeConfig = computed(() => mode.value === 'free' && !fixedPracticeEntry.value)

  const selectedSpecificDimensions = computed(() => selectedDimensions.value.filter((item) => item && item !== RANDOM_DIMENSION_KEY))

  const selectedDimensionParam = computed(() => selectedSpecificDimensions.value.join(','))

  const selectedCategoryName = computed(() => {
    if (!selectedSpecificDimensions.value.length) return '随机题型'
    const names = selectedSpecificDimensions.value
      .map((key) => questionCategoryOptions.find((item) => item.key === key)?.name)
      .filter(Boolean)
    return names.join('、') || '随机题型'
  })

  watch(() => userStore.preferences?.preferredQuestionDimensions, () => {
    applyPreferredQuestionDimensions()
  }, { immediate: true, deep: true })

  const examCategoryOptions = DEFAULT_TARGETED_POSITION_TREE
  const examCategoryNames = computed(() => ['不限', ...examCategoryOptions.map(c => c.name)])
  const examCategoryIndex = computed(() => {
    const idx = examCategoryOptions.findIndex(c => String(c.id) === String(selectedExamCategoryId.value))
    return idx >= 0 ? idx + 1 : 0
  })
  const selectedExamCategoryName = computed(() => {
    const cat = examCategoryOptions.find(c => String(c.id) === String(selectedExamCategoryId.value))
    return cat ? cat.name : '不限'
  })
  const selectedCategoryNode = computed(() =>
    selectedExamCategoryId.value
      ? examCategoryOptions.find(c => String(c.id) === String(selectedExamCategoryId.value)) || null
      : null
  )
  function uniqueRegionsFromTree() {
    const seen = new Set()
    const regions = []
    examCategoryOptions.forEach((category) => {
      ;(category.children || []).forEach((region) => {
        const province = normalizeProvinceCode(region.province || '')
        if (!province || province === 'all') return
        if (seen.has(province)) return
        seen.add(province)
        regions.push({
          id: `region_${province}`,
          name: region.name || province,
          province
        })
      })
    })
    return regions
  }
  const regionOptions = computed(() => uniqueRegionsFromTree())
  const regionNames = computed(() => ['不限', ...regionOptions.value.map(r => r.name)])
  const regionIndex = computed(() => {
    const idx = regionOptions.value.findIndex(r => String(r.id) === String(selectedRegionId.value))
    return idx >= 0 ? idx + 1 : 0
  })
  const selectedRegionNameText = computed(() => {
    const r = regionOptions.value.find(r => String(r.id) === String(selectedRegionId.value))
    return r ? r.name : '不限'
  })
  const selectedRegionNode = computed(() =>
    selectedRegionId.value
      ? regionOptions.value.find(r => String(r.id) === String(selectedRegionId.value)) || null
      : null
  )
  function findCategoryByPreference(value = '') {
  const text = String(value || '').trim()
  if (!text) return null
  return examCategoryOptions.find((category) => (
    String(category.id) === text
    || String(category.name) === text
    || String(category.examCategory || '') === text
  )) || null
}
  function matchingTreeRegions() {
  const region = selectedRegionNode.value
  if (!region) return []
  const categories = selectedCategoryNode.value ? [selectedCategoryNode.value] : examCategoryOptions
  return categories.flatMap((category) => (
    (category.children || []).filter((item) => normalizeProvinceCode(item.province || '') === region.province)
  ))
}
  const directionOptions = computed(() => {
  const seen = new Set()
  const options = []
  matchingTreeRegions().forEach((region) => {
    const directions = Array.isArray(region.directions)
      ? region.directions
      : Array.isArray(region.children)
        ? region.children
        : []
    directions.forEach((direction) => {
      const id = String(direction.id || `${region.id}_${direction.name}`)
      if (seen.has(id)) return
      seen.add(id)
      options.push(direction)
    })
  })
  return options
})
  const hasDirectionOptions = computed(() => directionOptions.value.length > 0)
  const directionNames = computed(() => ['不限', ...directionOptions.value.map(d => d.name)])
  const directionIndex = computed(() => {
    const idx = directionOptions.value.findIndex(d => String(d.id) === String(selectedDirectionId.value))
    return idx >= 0 ? idx + 1 : 0
  })
  const selectedDirectionNameText = computed(() => {
    const d = directionOptions.value.find(d => String(d.id) === String(selectedDirectionId.value))
    return d ? d.name : '不限'
  })
  const selectedDirectionNode = computed(() =>
    selectedDirectionId.value
      ? directionOptions.value.find(d => String(d.id) === String(selectedDirectionId.value)) || null
      : null
  )
  const yearOptions = computed(() =>
    filterMetadata.options.value.year.map(y => ({ value: y, checked: selectedYearsFilter.value.includes(y) }))
  )
  const yearLabel = computed(() =>
    selectedYearsFilter.value.length ? selectedYearsFilter.value.join('、') : '不限年份（可多选）'
  )

  // Build target filter params for API calls
  const targetFilterParams = computed(() => {
  if (fixedPracticeEntry.value) return selection.value.filters
  const params = {}
  const cat = selectedCategoryNode.value
  const region = selectedRegionNode.value
  const dir = selectedDirectionNode.value
  if (cat) params.examCategory = cat.examCategory || cat.name
  if (region) {
    if (region.province) params.province = region.province
  }
  if (dir) {
    if (dir.examSubcategory) params.examSubcategory = dir.examSubcategory
    if (dir.subcategory) params.subcategory = dir.subcategory
    if (dir.subcategory2) params.subcategory2 = dir.subcategory2
    if (!dir.subcategory && !dir.subcategory2) params.subcategory2 = dir.name
    if (dir.position) params.position = dir.position
    if (dir.province) params.province = dir.province
  }
  if (mode.value !== 'fullExam' && selectedYearsFilter.value.length) params.year = selectedYearsFilter.value.join(',')
  return params
})

  // Use the same effective scope as fetchRandom; keep its province fallback and
  // exact dimension parameter, but exclude the year facet's own selection.
  const metadataFilterParams = computed(() => ({
    province: targetFilterParams.value.province || userStore.selectedProvince,
    dimension: selectedDimensionParam.value,
    ...targetFilterParams.value,
    year: ''
  }))
  function refreshFilterMetadata() {
    return filterMetadata.refresh(metadataFilterParams.value, hasFullAccess.value && userStore.isAuthenticated)
  }
  // Do not request on every checkbox change: a facet excludes its own year filter.
  watch(() => JSON.stringify({ ...metadataFilterParams.value, access: hasFullAccess.value && userStore.isAuthenticated }), refreshFilterMetadata, { immediate: true })

  function applyDefaultTargetFilters(force = false) {
    if (targetFilterTouched.value && !force) return
    const preferredCategory = findCategoryByPreference(userStore.preferences?.examCategory)
    selectedExamCategoryId.value = preferredCategory?.id || ''
    const preferredProvince = normalizeProvinceCode(userStore.selectedProvince || '')
    if (preferredProvince && preferredProvince !== 'all') {
      selectedRegionId.value = regionOptions.value.find((region) => region.province === preferredProvince)?.id || ''
    } else {
      selectedRegionId.value = ''
    }
    selectedDirectionId.value = ''
  }

  watch(() => [userStore.selectedProvince, userStore.preferences?.examCategory], () => {
    applyDefaultTargetFilters()
  }, { immediate: true })

  function onExamCategoryFilterChange(e) {
    targetFilterTouched.value = true
    const idx = Number(e.detail.value)
    if (idx === 0) {
      selectedExamCategoryId.value = ''
    } else {
      const cat = examCategoryOptions[idx - 1]
      selectedExamCategoryId.value = cat ? cat.id : ''
    }
    selectedDirectionId.value = ''
  }
  function onRegionFilterChange(e) {
    targetFilterTouched.value = true
    const idx = Number(e.detail.value)
    if (idx === 0) {
      selectedRegionId.value = ''
    } else {
      const r = regionOptions.value[idx - 1]
      selectedRegionId.value = r ? r.id : ''
    }
    selectedDirectionId.value = ''
  }
  function onDirectionFilterChange(e) {
    targetFilterTouched.value = true
    const idx = Number(e.detail.value)
    if (idx === 0) {
      selectedDirectionId.value = ''
    } else {
      const d = directionOptions.value[idx - 1]
      selectedDirectionId.value = d ? d.id : ''
    }
  }
  function onYearFilterChange(e) {
    selectedYearsFilter.value = e.detail.value || []
  }

  function applyPreferredQuestionDimensions() {
    if (questionTypeTouched.value || !showPracticeConfig.value) return
    const validKeys = new Set(questionCategoryOptions.map((item) => item.key).filter((item) => item && item !== RANDOM_DIMENSION_KEY))
    const preferred = Array.isArray(userStore.preferences?.preferredQuestionDimensions)
      ? userStore.preferences.preferredQuestionDimensions
        .map((item) => String(item || '').trim())
        .filter((item, index, list) => validKeys.has(item) && list.indexOf(item) === index)
      : []
    selectedDimensions.value = preferred.length ? preferred : [RANDOM_DIMENSION_KEY]
  }

  function isTypeSelected(key) {
    return selectedDimensions.value.includes(key)
  }

  function toggleQuestionType(key) {
    questionTypeTouched.value = true
    if (key === RANDOM_DIMENSION_KEY) {
      if (selectedSpecificDimensions.value.length) return
      selectedDimensions.value = [RANDOM_DIMENSION_KEY]
      return
    }

    const specific = selectedSpecificDimensions.value
    if (specific.includes(key)) {
      const next = specific.filter((item) => item !== key)
      selectedDimensions.value = next.length ? next : [RANDOM_DIMENSION_KEY]
      return
    }

    selectedDimensions.value = [...specific, key]
  }

  return {
    selectedDimensions,
    selectedSpecificDimensions,
    selectedDimensionParam,
    selectedCategoryName,
    questionCategoryOptions,
    showPracticeConfig,
    examCategoryOptions,
    examCategoryNames,
    examCategoryIndex,
    selectedExamCategoryName,
    regionOptions,
    regionNames,
    regionIndex,
    selectedRegionNameText,
    directionOptions,
    hasDirectionOptions,
    directionNames,
    directionIndex,
    selectedDirectionNameText,
    selectedYearsFilter,
    yearOptions,
    yearLabel,
    targetFilterParams,
    refreshFilterMetadata,
    onExamCategoryFilterChange,
    onRegionFilterChange,
    onDirectionFilterChange,
    onYearFilterChange,
    applyPreferredQuestionDimensions,
    isTypeSelected,
    toggleQuestionType
  }
}
