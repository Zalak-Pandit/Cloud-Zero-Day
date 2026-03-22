const BASE = '/api/v1'

async function req(path, opts = {}) {
  const res = await fetch(BASE + path, {
    headers: { 'Content-Type': 'application/json' },
    ...opts,
  })
  if (!res.ok) throw new Error(`API error ${res.status}`)
  return res.json()
}

export const api = {
  threats: {
    list: (params = {}) => {
      const q = new URLSearchParams(params).toString()
      return req(`/threats${q ? '?' + q : ''}`)
    },
    stats: () => req('/threats/stats'),
    get: (id) => req(`/threats/${id}`),
    updateStatus: (id, status) => req(`/threats/${id}/status?status=${status}`, { method: 'PATCH' }),
    simulate: () => req('/threats/simulate', { method: 'POST' }),
  },
  metrics: {
    timeseries: (hours = 24) => req(`/metrics/timeseries?hours=${hours}`),
    modelPerformance: () => req('/metrics/model-performance'),
  },
}

export function createWS(onMessage) {
  const protocol = location.protocol === 'https:' ? 'wss' : 'ws'
  const ws = new WebSocket(`${protocol}://${location.host}/ws/threats`)
  ws.onmessage = (e) => {
    try { onMessage(JSON.parse(e.data)) } catch {}
  }
  ws.onerror = (e) => console.warn('WS error', e)
  return ws
}