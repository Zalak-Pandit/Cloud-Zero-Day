import { useState, useEffect, useCallback, useRef } from 'react'
import { Shield, Wifi, WifiOff, RefreshCw, Play } from 'lucide-react'
import MetricsBar from './components/MetricsBar'
import ThreatFeed from './components/ThreatFeed'
import ThreatDetail from './components/ThreatDetail'
import { ThreatTimeline, ModelPerformanceChart } from './components/AnomalyChart'
import { api, createWS } from './api/client'

// ─── Global styles ───────────────────────────────────────────────────────────
const style = document.createElement('style')
style.textContent = `
  *, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }
  :root {
    --bg:        #020817;
    --surface:   #0a0f1e;
    --card-bg:   #0d1526;
    --card-hover:#111a30;
    --border:    #1e293b;
    --text:      #e2e8f0;
    --muted:     #64748b;
    --accent:    #6366f1;
  }
  body { background: var(--bg); color: var(--text); font-family: system-ui, -apple-system, sans-serif; }
  ::-webkit-scrollbar { width: 4px; height: 4px; }
  ::-webkit-scrollbar-track { background: transparent; }
  ::-webkit-scrollbar-thumb { background: var(--border); border-radius: 2px; }
  @keyframes pulse-dot { 0%,100%{opacity:1} 50%{opacity:.3} }
  @keyframes slide-in  { from{transform:translateY(-8px);opacity:0} to{transform:none;opacity:1} }
`
document.head.appendChild(style)

const POLL_INTERVAL = 15_000   // refresh stats every 15s

export default function App() {
  const [threats,      setThreats]      = useState([])
  const [stats,        setStats]        = useState(null)
  const [timeseries,   setTimeseries]   = useState([])
  const [modelPerf,    setModelPerf]    = useState(null)
  const [selected,     setSelected]     = useState(null)
  const [wsStatus,     setWsStatus]     = useState('connecting')
  const [simulating,   setSimulating]   = useState(false)
  const wsRef = useRef(null)

  // ── Data fetchers ──────────────────────────────────────────────────────────
  const fetchThreats = useCallback(async () => {
    try {
      const res = await api.threats.list({ page_size: 100 })
      setThreats(res.threats || [])
    } catch {}
  }, [])

  const fetchStats = useCallback(async () => {
    try {
      const [s, ts, mp] = await Promise.all([
        api.threats.stats(),
        api.metrics.timeseries(24),
        api.metrics.modelPerformance(),
      ])
      setStats(s)
      setTimeseries(ts)
      setModelPerf(mp)
    } catch {}
  }, [])

  // ── WebSocket ──────────────────────────────────────────────────────────────
  useEffect(() => {
    let retryTimeout

    function connect() {
      const ws = createWS((msg) => {
        if (msg.type === 'new_threat' && msg.threat) {
          setThreats(prev => [msg.threat, ...prev.slice(0, 499)])
          fetchStats()
        }
      })
      ws.onopen  = () => setWsStatus('connected')
      ws.onclose = () => {
        setWsStatus('disconnected')
        retryTimeout = setTimeout(connect, 3000)
      }
      wsRef.current = ws
    }

    connect()
    return () => {
      clearTimeout(retryTimeout)
      wsRef.current?.close()
    }
  }, [fetchStats])

  // ── Initial + polling ──────────────────────────────────────────────────────
  useEffect(() => {
    fetchThreats()
    fetchStats()
    const iv = setInterval(fetchStats, POLL_INTERVAL)
    return () => clearInterval(iv)
  }, [fetchThreats, fetchStats])

  // ── Simulate threat ────────────────────────────────────────────────────────
  async function simulate() {
    setSimulating(true)
    try { await api.threats.simulate() } catch {}
    setTimeout(() => setSimulating(false), 800)
  }

  // ── Layout ─────────────────────────────────────────────────────────────────
  return (
    <div style={{ minHeight: '100vh', display: 'flex', flexDirection: 'column', padding: '20px 24px' }}>

      {/* ── Header ── */}
      <header style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 24 }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
          <div style={{ position: 'relative' }}>
            <Shield size={28} color="#6366f1" />
            <span style={{
              position: 'absolute', bottom: -1, right: -1,
              width: 8, height: 8, borderRadius: '50%',
              background: wsStatus === 'connected' ? '#22c55e' : '#ef4444',
              border: '1.5px solid var(--bg)',
              animation: wsStatus === 'connected' ? 'pulse-dot 2s infinite' : 'none',
            }} />
          </div>
          <div>
            <h1 style={{ fontSize: 20, fontWeight: 800, letterSpacing: '-0.02em', color: '#e2e8f0' }}>
              Cloud<span style={{ color: '#6366f1' }}>Sentinel</span>
            </h1>
            <p style={{ fontSize: 11, color: 'var(--muted)', marginTop: 1 }}>Zero-Day Threat Detection Platform</p>
          </div>
        </div>

        <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
          {/* WS status */}
          <div style={{ display: 'flex', alignItems: 'center', gap: 5, fontSize: 11, color: 'var(--muted)' }}>
            {wsStatus === 'connected'
              ? <><Wifi size={12} color="#22c55e" /><span style={{ color: '#22c55e' }}>Live</span></>
              : <><WifiOff size={12} color="#ef4444" /><span style={{ color: '#ef4444' }}>Reconnecting</span></>
            }
          </div>

          {/* Refresh */}
          <button onClick={fetchStats} style={btnStyle}>
            <RefreshCw size={12} /> Refresh
          </button>

          {/* Simulate */}
          <button onClick={simulate} disabled={simulating} style={{ ...btnStyle, background: '#312e81', borderColor: '#4338ca', color: '#a5b4fc' }}>
            <Play size={12} /> {simulating ? 'Injecting...' : 'Simulate Threat'}
          </button>
        </div>
      </header>

      {/* ── Metrics bar ── */}
      <MetricsBar stats={stats} />

      {/* ── Main grid ── */}
      <div style={{ display: 'grid', gridTemplateColumns: '1fr 380px', gap: 16, flex: 1, minHeight: 0 }}>

        {/* Left column */}
        <div style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>

          {/* Chart card */}
          <div style={cardStyle}>
            <div style={cardHeaderStyle}>
              <span>Threat Timeline — Last 24h</span>
            </div>
            <ThreatTimeline data={timeseries} />
          </div>

          {/* Model performance + threat type breakdown */}
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 16 }}>
            <div style={cardStyle}>
              <div style={cardHeaderStyle}><span>ML Model Avg Scores</span></div>
              <ModelPerformanceChart data={modelPerf} />
            </div>
            <div style={cardStyle}>
              <div style={cardHeaderStyle}><span>Top Threat Types</span></div>
              <div style={{ display: 'flex', flexDirection: 'column', gap: 6, marginTop: 4 }}>
                {(stats?.top_threat_types || []).slice(0, 5).map((tt, i) => (
                  <div key={tt.type} style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                    <span style={{ fontSize: 10, color: 'var(--muted)', minWidth: 14 }}>{i + 1}</span>
                    <div style={{ flex: 1 }}>
                      <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 3 }}>
                        <span style={{ fontSize: 11, color: 'var(--text)' }}>
                          {tt.type.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase())}
                        </span>
                        <span style={{ fontSize: 11, color: 'var(--muted)', fontFamily: 'monospace' }}>{tt.count}</span>
                      </div>
                      <div style={{ height: 3, background: 'var(--border)', borderRadius: 2 }}>
                        <div style={{
                          height: '100%', borderRadius: 2, background: '#6366f1',
                          width: `${Math.round((tt.count / Math.max(...(stats?.top_threat_types || [{ count: 1 }]).map(x => x.count))) * 100)}%`,
                        }} />
                      </div>
                    </div>
                  </div>
                ))}
                {!stats?.top_threat_types?.length && (
                  <div style={{ color: 'var(--muted)', fontSize: 12, padding: '16px 0', textAlign: 'center' }}>No data yet</div>
                )}
              </div>
            </div>
          </div>

          {/* Threat feed */}
          <div style={{ ...cardStyle, flex: 1, minHeight: 0 }}>
            <div style={cardHeaderStyle}>
              <span>Live Threat Feed</span>
              <span style={{ fontSize: 11, color: 'var(--muted)', fontFamily: 'monospace' }}>{threats.length} events</span>
            </div>
            <ThreatFeed threats={threats} onSelect={setSelected} selected={selected} />
          </div>
        </div>

        {/* Right column — detail panel */}
        <div style={{ ...cardStyle, position: 'sticky', top: 20, height: 'fit-content', maxHeight: 'calc(100vh - 40px)', overflow: 'hidden' }}>
          <div style={cardHeaderStyle}><span>Threat Detail</span></div>
          <ThreatDetail
            threat={selected}
            onClose={() => setSelected(null)}
            onStatusChange={() => { fetchThreats(); fetchStats() }}
          />
        </div>
      </div>
    </div>
  )
}

const cardStyle = {
  background: 'var(--card-bg)',
  border: '1px solid var(--border)',
  borderRadius: 12,
  padding: '16px 18px',
  display: 'flex',
  flexDirection: 'column',
  gap: 12,
}

const cardHeaderStyle = {
  display: 'flex',
  alignItems: 'center',
  justifyContent: 'space-between',
  fontSize: 12,
  fontWeight: 700,
  color: '#94a3b8',
  textTransform: 'uppercase',
  letterSpacing: '0.06em',
  marginBottom: 4,
}

const btnStyle = {
  display: 'flex', alignItems: 'center', gap: 5,
  padding: '6px 12px', fontSize: 11, fontWeight: 600,
  borderRadius: 6, cursor: 'pointer',
  background: 'var(--card-bg)', border: '1px solid var(--border)',
  color: 'var(--muted)', transition: 'all 0.15s',
}