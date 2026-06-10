/**
 * PC 定向备面状态仓库，保存考试体系分类树、用户选择、重点分析结果和生成训练题状态。
 *
 * 这里维护的是筛选与展示状态，不负责改写题库真实分类。方向允许“不限”，无题库数据时保留空态，不能用通用模板伪造重点分析。
 * 管理员发布内容和自动统计结果都来自后端，前端只做展示和刷新。
 *
 * @param 无；actions 接收分类选择、重点分析请求或生成训练题参数。
 * @return 导出 Pinia store，供定向页、重点分析页和管理员定向页复用。
 * @raises Error: 分类加载、重点分析或题目生成失败时由 action 抛给页面处理。
 */
import { defineStore } from 'pinia'
import { getPositions, getFocusAnalysis, generateQuestions } from '@/api/targeted'
import { DEFAULT_TARGETED_POSITION_TREE, normalizeTargetPayload } from '@/utils/targetedOptions'

export const useTargetedStore = defineStore('targeted', {
  state: () => ({
    selectedProvince: '',
    selectedPosition: '',
    selectedTarget: null,
    positionTree: DEFAULT_TARGETED_POSITION_TREE,
    legacyPositions: [],
    positionsLoaded: false,
    focusData: null,
    focusLoading: false,
    generatedQuestions: [],
    generateLoading: false
  }),

  getters: {
    hasSelection(state) {
      if (state.selectedTarget?.targetCode) return true
      return !!state.selectedProvince && state.selectedPosition !== ''
    },
    selectionPayload(state) {
      if (state.selectedTarget?.targetCode) {
        return normalizeTargetPayload(state.selectedTarget)
      }
      return normalizeTargetPayload({
        province: state.selectedProvince,
        position: state.selectedPosition,
        targetCode: state.selectedPosition || state.selectedProvince,
        targetName: state.selectedPosition || state.selectedProvince
      })
    }
  },

  actions: {
    setSelection(province, position) {
      this.selectedProvince = province
      this.selectedPosition = position
      this.selectedTarget = null
      this.focusData = null
      this.generatedQuestions = []
    },

    setTarget(target) {
      const payload = normalizeTargetPayload(target)
      this.selectedTarget = payload
      this.selectedProvince = payload.province
      this.selectedPosition = payload.position
      this.focusData = null
      this.generatedQuestions = []
    },

    async fetchPositionTree() {
      try {
        const response = await getPositions()
        const tree = Array.isArray(response?.tree) ? response.tree : []
        this.positionTree = tree.length ? tree : DEFAULT_TARGETED_POSITION_TREE
        this.legacyPositions = Array.isArray(response?.legacy) ? response.legacy : []
      } catch (error) {
        this.positionTree = DEFAULT_TARGETED_POSITION_TREE
      } finally {
        this.positionsLoaded = true
      }
      return this.positionTree
    },

    async fetchFocusAnalysis() {
      if (!this.hasSelection) return
      this.focusLoading = true
      try {
        this.focusData = await getFocusAnalysis(this.selectionPayload)
      } finally {
        this.focusLoading = false
      }
    },

    async fetchGeneratedQuestions(count = 5) {
      if (!this.hasSelection) return
      this.generateLoading = true
      try {
        this.generatedQuestions = await generateQuestions({
          ...this.selectionPayload,
          count,
          sourceMode: 'local'
        })
        return this.generatedQuestions
      } finally {
        this.generateLoading = false
      }
    }
  }
})
