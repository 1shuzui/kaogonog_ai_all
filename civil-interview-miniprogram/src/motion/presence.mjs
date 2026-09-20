// A small interruptible presence controller: CSS owns frames; JS owns only edges.
export function createPresence({ publish, schedule = setTimeout, cancel = clearTimeout }) {
  let id = 0
  let target = false
  let timer = null
  let disposed = false
  let state = { mounted: false, interactive: false, phase: 'hidden', id }
  function finish(expected = id) {
    if (disposed || expected !== id) return
    if (timer !== null) cancel(timer)
    timer = null
    const phase = target ? 'shown' : 'hidden'
    if (state.phase === phase) return
    state = { mounted: target, interactive: target, phase, id }
    publish(state)
  }
  function set(visible, duration) {
    if (disposed) return
    target = !!visible
    if (timer !== null) cancel(timer)
    timer = null
    id += 1
    state = { mounted: target || state.mounted, interactive: target, phase: target ? 'entering' : 'leaving', id }
    publish(state)
    if (!duration || !state.mounted) { finish(id); return }
    const expected = id
    timer = schedule(() => finish(expected), duration)
  }
  function dispose() { disposed = true; id += 1; if (timer !== null) cancel(timer); timer = null }
  return { set, finish, dispose }
}
