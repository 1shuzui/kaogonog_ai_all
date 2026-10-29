// Platform-neutral review state. Pinia, storage and HTTP are injected by each client.
export function createReviewStore({ read, write, api, message = error => error?.normalizedMessage || error?.message || '同步失败，请重试' }) {
  const identity = () => ({ userId: String(read('civil_user_id') || ''), token: String(read('token') || '') })
  const same = (a, b) => a.userId === b.userId && a.token === b.token && !!a.userId && !!a.token
  const snapshotKey = id => `civil_reviews_v1:${id}`
  const parse = key => { try { return JSON.parse(read(key) || 'null') } catch { return null } }
  const persist = (key, value) => { try { write(key, JSON.stringify(value)) } catch { /* Server remains authoritative. */ } }
  const stale = () => Object.assign(new Error('账号已切换，请刷新当前页面'), { code: 'STALE_SESSION' })
  const check = (owner, response) => {
    if (!same(owner, identity()) || (response && String(response.userId) !== owner.userId)) throw stale()
  }

  return {
    state: () => ({ items: [], ownerId: '', ownerToken: '', loading: false, saving: false, error: '', revision: 0, migrationNotice: '' }),
    getters: {
      count: state => state.items.filter(item => item.isWeak || item.isStarred).length,
      weakItems: state => state.items.filter(item => item.isWeak),
      starredItems: state => state.items.filter(item => item.isStarred),
      isFavorited: state => (examId, questionId) => state.items.some(item => item.examId === examId && item.questionId === questionId && item.isStarred)
    },
    actions: {
      reloadForCurrentUser() {
        const owner = identity()
        this.revision++
        this.ownerId = owner.userId
        this.ownerToken = owner.token
        this.loading = this.saving = false
        this.error = this.migrationNotice = ''
        const cached = owner.userId && owner.token ? parse(snapshotKey(owner.userId)) : null
        this.items = cached?.userId === owner.userId && Array.isArray(cached.items) ? cached.items : []
      },
      async migrateLegacy(owner) {
        const marker = `civil_reviews_import_v1:${owner.userId}`
        if (parse(marker)?.complete) return
        const username = String(read('username') || '')
        const candidates = [parse('civil_favorites'), username ? parse(`civil_favorites:${username}`) : null]
          .flatMap(items => Array.isArray(items) ? items : [])
          .filter(item => item && typeof item.examId === 'string' && item.examId.length <= 32 && typeof item.questionId === 'string' && item.questionId.length <= 128)
          .map(item => ({ examId: item.examId, questionId: item.questionId, isStarred: item.isStarred ?? ['starred', 'favorite'].includes(item.type) }))
        let rejected = 0
        for (let index = 0; index < candidates.length; index += 200) {
          check(owner)
          const result = await api.importItems(candidates.slice(index, index + 200))
          check(owner, result)
          rejected += Number(result.rejected || 0)
        }
        check(owner)
        persist(marker, { complete: true, rejected })
        if (rejected) this.migrationNotice = '部分旧记录无法核实归属，已保留原缓存但未导入。'
      },
      async load() {
        const owner = identity()
        if (!same(owner, { userId: this.ownerId, token: this.ownerToken })) this.reloadForCurrentUser()
        if (!owner.userId || !owner.token) return false
        const revision = ++this.revision
        this.loading = true
        this.error = ''
        try {
          await this.migrateLegacy(owner)
          const items = new Map()
          let current = 1, total = 0, received = 0
          do {
            check(owner)
            const result = await api.list({ current, pageSize: 200 })
            check(owner, result)
            if (!Array.isArray(result.list) || !Number.isFinite(Number(result.total))) throw new Error('复习记录格式异常，请重试')
            total = Number(result.total)
            for (const item of result.list) items.set(item.id, item)
            received += result.list.length
            if (!result.list.length) break
            current++
          } while (received < total)
          if (revision !== this.revision) return false
          this.items = [...items.values()]
          persist(snapshotKey(owner.userId), { userId: owner.userId, items: this.items })
          return true
        } catch (error) {
          if (same(owner, identity()) && revision === this.revision && error?.code !== 'STALE_SESSION') this.error = message(error)
          return false
        } finally {
          if (same(owner, identity()) && revision === this.revision) this.loading = false
        }
      },
      async mutate(operation) {
        const owner = identity()
        if (!owner.userId || !owner.token) return false
        if (!same(owner, { userId: this.ownerId, token: this.ownerToken })) this.reloadForCurrentUser()
        if (this.saving) return false
        this.saving = true
        this.error = ''
        let saved = false
        try {
          const response = await operation()
          check(owner, response)
          saved = true
          if (!await this.load() && same(owner, identity()) && this.error) this.error = '操作已保存，列表刷新失败，请重试刷新。'
          check(owner)
          return true
        } catch (error) {
          if (same(owner, identity()) && error?.code !== 'STALE_SESSION') this.error = saved ? '操作已保存，列表刷新失败，请重试刷新。' : `未保存：${message(error)}`
          return false
        } finally {
          if (same(owner, identity())) this.saving = false
        }
      },
      addItem({ examId, questionId, type = 'weak' }) {
        if (type === 'weak') return this.load()
        return this.mutate(() => api.update({ examId, questionId, isStarred: true }))
      },
      removeItem(id, type = 'all') {
        const item = this.items.find(entry => entry.id === id)
        if (!item) return Promise.resolve(false)
        const body = { examId: item.examId, questionId: item.questionId }
        if (type === 'all' || type === 'starred') body.isStarred = false
        if (type === 'all' || type === 'weak') body.hideWeak = true
        return this.mutate(() => api.update(body))
      },
      clearAll(scope = 'all') { return this.mutate(() => api.clear(scope)) }
    }
  }
}
