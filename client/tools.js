export function assert (condition, message) {
  if (!condition) {
    throw new Error(message)
  }
}

export function observable () {
  const subs = {}
  return {
    on (eventName, handler) {
      if (!subs[eventName]) {
        subs[eventName] = []
      }
      subs[eventName].push(handler)
    },
    off (eventName, handler) {
      const idx = (subs[eventName] || []).indexOf(handler)
      if (idx !== -1) {
        subs[eventName].splice(idx, 1)
      }
    },
    notify (eventName, payload) {
      (subs[eventName] || []).forEach(handler => handler(payload))
    },
  }
}

export function deepMapper (cb) {
  return item => Array.isArray(item) ? item.map(deepMapper(cb)) : cb(item)
}
