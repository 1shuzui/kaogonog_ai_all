// Logic-layer cancellation, independent of browser AbortController/DOM support.
export function createCancellation() {
  const listeners = new Set()
  const signal = {
    aborted: false,
    subscribe(listener) {
      if (signal.aborted) { listener(); return () => {} }
      listeners.add(listener)
      return () => listeners.delete(listener)
    }
  }
  return {
    signal,
    cancel() {
      if (signal.aborted) return
      signal.aborted = true
      for (const listener of [...listeners]) listener()
      listeners.clear()
    }
  }
}
