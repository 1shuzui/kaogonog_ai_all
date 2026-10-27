// Platform-independent queue. No Page/Component instances are retained here.
function createNavigator({ readRoute, navigate, notify, schedule = setTimeout, cancel = clearTimeout, now = Date.now, timeoutMs = 3000 }) {
  let confirmed = readRoute()
  let desired = confirmed
  let requestId = 0
  let flight = null
  let transition = null
  const snapshot = () => ({ confirmed, desired, requestId, pending: !!flight, transition })
  function emit() {
    // A component may be between detach/ready while native navigation completes.
    // Its render must never leave the shared navigation queue permanently locked.
    try { notify(snapshot()) } catch (error) { console.warn('底部导航状态同步失败', error) }
  }
  function sync() {
    confirmed = readRoute()
    if (!flight) {
      desired = confirmed
      if (transition?.to !== confirmed) transition = null
    }
    return snapshot()
  }
  function drain() {
    if (flight) return
    confirmed = readRoute()
    if (desired === confirmed) { emit(); return }
    const current = { id: ++requestId, target: desired, timer: null }
    flight = current
    transition = { id: current.id, from: confirmed, to: desired, startedAt: now() }
    const done = (success) => {
      if (flight !== current) return
      cancel(current.timer)
      flight = null
      confirmed = readRoute()
      // Abandon only THIS request, never a newer user's target.
      if (desired === current.target && (!success || confirmed !== current.target)) desired = confirmed
      if (confirmed !== current.target) transition = null
      emit()
      drain()
    }
    current.done = done
    // Login redirects, backgrounding or an interrupted native callback must not
    // block every subsequent tap. The actual page is the source of truth.
    current.timer = schedule(() => done(readRoute() === current.target), timeoutMs)
    emit()
    try { navigate(current.target, done) } catch { done(false) }
  }
  function request(target) {
    // Do this even when target === confirmed: A→B→A must queue the return to A.
    desired = target
    if (flight && readRoute() === flight.target) {
      flight.done(true)
      return
    }
    if (flight) emit()
    drain()
  }
  return { request, sync, snapshot }
}

module.exports = { createNavigator }
