// Platform-independent queue. No Page/Component instances are retained here.
function createNavigator({ readRoute, navigate, notify }) {
  let confirmed = readRoute()
  let desired = confirmed
  let requestId = 0
  let flight = null
  const snapshot = () => ({ confirmed, desired, requestId, pending: !!flight })
  function sync() {
    confirmed = readRoute()
    if (!flight) desired = confirmed
    return snapshot()
  }
  function drain() {
    if (flight) return
    confirmed = readRoute()
    if (desired === confirmed) { notify(snapshot()); return }
    const current = { id: ++requestId, target: desired }
    flight = current
    notify(snapshot())
    const done = (success) => {
      if (flight !== current) return
      flight = null
      confirmed = readRoute()
      // On failure, abandon only THIS request, never a newer user's target.
      if (!success && desired === current.target) desired = confirmed
      if (success && confirmed !== current.target && desired === current.target) desired = confirmed
      notify(snapshot())
      drain()
    }
    try { navigate(current.target, done) } catch { done(false) }
  }
  function request(target) {
    // Do this even when target === confirmed: A→B→A must queue the return to A.
    desired = target
    if (flight) notify(snapshot())
    drain()
  }
  return { request, sync, snapshot }
}

module.exports = { createNavigator }
