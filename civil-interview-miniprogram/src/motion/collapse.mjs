// CSS owns the height frames. JS measures endpoints and handles interruption only.
export function createCollapse({ open = false, measure, publish, settled = () => {}, slack = 80, now = Date.now, schedule = setTimeout, cancel = clearTimeout }) {
  let id = 0, target = open, timer, active = true, disposed = false, natural = 0, started = 0
  let state = { id, mounted: open, interactive: open, phase: open ? 'open' : 'closed', height: open ? 'auto' : '0px', from: 0, to: 0, duration: 0, animation: 0 }
  const emit = patch => { state = { ...state, ...patch }; publish(state) }
  const clear = () => { if (timer != null) cancel(timer); timer = null }
  publish(state)
  function finish(expected) {
    if (disposed || !active || expected !== id) return false
    clear()
    if (target) natural = state.to
    emit({ id, phase: target ? 'open' : 'closed', height: target ? 'auto' : '0px', mounted: target, interactive: target, duration: 0 })
    settled(target)
    return true
  }
  function complete(expected) {
    if (!['opening', 'closing'].includes(state.phase) || now() - started < state.duration - 20) return false
    return finish(expected)
  }
  function set(value, duration = 280, resizing = false) {
    target = !!value
    if (disposed || !active) return
    const expected = ++id
    clear()
    if (!state.mounted && !target) return
    if (!state.mounted) emit({ mounted: true, height: '0px', interactive: false })
    // Revision watchers run before slot patching: reserve the old loading/result
    // height before replacing content, not after it has already collapsed.
    if (resizing && state.phase === 'open' && natural > 0) emit({ height: `${natural}px`, phase: 'prepared' })
    Promise.resolve(measure()).then(geometry => {
      if (disposed || !active || expected !== id) return
      const from = Math.max(0, Number(geometry?.outer) || 0)
      const to = target ? Math.max(0, Number(geometry?.inner) || 0) : 0
      started = now()
      const animated = duration > 0 && geometry && Math.abs(from - to) > .5
      emit({ id, from, to, height: `${to}px`, duration: animated ? duration : 0,
        mounted: true, interactive: target, phase: target ? 'opening' : 'closing', animation: state.animation + 1 })
      if (!animated) { finish(expected); return }
      timer = schedule(() => finish(expected), duration + slack)
    }, () => { if (expected === id) finish(expected) })
  }
  function resize(duration = 280) { if (target) set(target, duration, true) }
  function pause() { active = false; id++; clear() }
  function resume(duration = 280) { if (disposed) return; active = true; set(target, duration) }
  function dispose() { disposed = true; pause() }
  return { set, resize, pause, resume, complete, dispose }
}
