import { defineStore } from 'pinia'
import { getPerformance } from '../api/targetedPerformance'
import { copy, reportKey } from '../utils/targetedPerformance.mjs'
import { createCancellation } from '../utils/cancellation.mjs'
import { TOKEN_STORAGE_KEY } from '../utils/constants'

const jobs = new WeakMap()
let sequence = 0
const session = () => uni.getStorageSync(TOKEN_STORAGE_KEY) || ''

export const useTargetedPerformanceStore = defineStore('targetedPerformance', {
  state: () => ({ target: null, period: 'recent30', report: null, status: 'idle', error: '', slow: false,
    requestId: 0, token: session(), scrollTop: 0, restorePosition: false, exams: {} }),
  actions: {
    clear() { this.cancel(); this.$reset() },
    setScope(target, period = this.period) {
      if (this.token !== session()) this.clear()
      if (reportKey(this.target, this.period) === reportKey(target, period)) return
      this.cancel()
      this.target = copy(target)
      this.period = period
      this.report = null
      this.error = ''
      this.status = 'idle'
      this.scrollTop = 0
    },
    cancel() {
      const job = jobs.get(this)
      if (!job) return
      this.requestId = ++sequence
      this.status = 'cancelled'
      this.slow = false
      this.error = '已停止等待，可重新分析。'
      job.cancel()
    },
    rememberExam(examId, context) {
      if (this.token !== session()) this.clear()
      const pages = typeof getCurrentPages === 'function' ? getCurrentPages() : []
      const origin = [...pages].reverse().find(page => ['pages/targeted/index', 'pages/targeted/focus'].includes(page.route))
      this.exams[examId] = copy({ ...context, returnView: {
        target: this.target || context.target, period: context.period,
        scrollTop: this.scrollTop, route: origin?.route || 'pages/targeted/focus'
      } })
    },
    contextFor(examId) { return this.token === session() ? this.exams[examId] || null : null },
    async fetch() {
      if (!this.target || !session()) return null
      this.cancel()
      const id = ++sequence, token = session(), key = reportKey(this.target, this.period)
      this.requestId = id
      this.status = 'loading'
      this.error = ''
      this.slow = false
      const cancellation = createCancellation()
      const owns = () => id === this.requestId && token === session() && key === reportKey(this.target, this.period)
      const timer = setTimeout(() => { if (owns()) this.slow = true }, 10000)
      const job = { cancel: () => { clearTimeout(timer); cancellation.cancel() } }
      jobs.set(this, job)
      try {
        const data = await getPerformance({ target: copy(this.target), period: this.period }, { signal: cancellation.signal })
        if (!owns()) return null
        this.report = data
        this.status = 'success'
        return data
      } catch (error) {
        if (!owns()) return null
        this.status = /timeout|超时/i.test(error?.message || '') ? 'timeout' : 'error'
        this.error = error?.message || '分析失败，请重试'
        return null
      } finally {
        clearTimeout(timer)
        if (owns()) this.slow = false
        if (jobs.get(this) === job) jobs.delete(this)
      }
    }
  }
})
