import {
  AreaChart, Area, BarChart, Bar, XAxis, YAxis, CartesianGrid,
  Tooltip, ResponsiveContainer, Legend
} from 'recharts'
import { format, parseISO } from 'date-fns'

const COLORS = {
  critical: '#ef4444',
  high:     '#f97316',
  medium:   '#eab308',
  low:      '#22c55e',
}

function CustomTooltip({ active, payload, label }) {
  if (!active || !payload?.length) return null
  return (
    <div style={{
      background: '#0f172a', border: '1px solid #1e293b',
      borderRadius: 8, padding: '8px 12px', fontSize: 11,
    }}>
      <div style={{ color: '#94a3b8', marginBottom: 4 }}>{label}</div>
      {payload.map(p => (
        <div key={p.dataKey} style={{ color: COLORS[p.dataKey] || p.color, display: 'flex', justifyContent: 'space-between', gap: 16 }}>
          <span style={{ textTransform: 'capitalize' }}>{p.dataKey}</span>
          <span style={{ fontWeight: 700 }}>{p.value}</span>
        </div>
      ))}
    </div>
  )
}

export function ThreatTimeline({ data }) {
  if (!data?.length) return <div style={{ height: 160, display: 'flex', alignItems: 'center', justifyContent: 'center', color: 'var(--muted)', fontSize: 12 }}>Loading...</div>

  const formatted = data.map(d => ({
    ...d,
    label: format(parseISO(d.time), 'HH:mm'),
  }))

  return (
    <ResponsiveContainer width="100%" height={160}>
      <AreaChart data={formatted} margin={{ top: 4, right: 0, left: -28, bottom: 0 }}>
        <defs>
          {Object.entries(COLORS).map(([k, c]) => (
            <linearGradient key={k} id={`grad-${k}`} x1="0" y1="0" x2="0" y2="1">
              <stop offset="5%" stopColor={c} stopOpacity={0.3} />
              <stop offset="95%" stopColor={c} stopOpacity={0} />
            </linearGradient>
          ))}
        </defs>
        <CartesianGrid strokeDasharray="3 3" stroke="#1e293b" />
        <XAxis dataKey="label" tick={{ fontSize: 10, fill: '#64748b' }} interval={3} />
        <YAxis tick={{ fontSize: 10, fill: '#64748b' }} />
        <Tooltip content={<CustomTooltip />} />
        {Object.entries(COLORS).map(([k, c]) => (
          <Area key={k} type="monotone" dataKey={k} stackId="1"
            stroke={c} fill={`url(#grad-${k})`} strokeWidth={1.5} />
        ))}
      </AreaChart>
    </ResponsiveContainer>
  )
}

export function ModelPerformanceChart({ data }) {
  if (!data) return null

  const chartData = [
    { name: 'Isolation Forest', score: Math.round((data.isolation_forest || 0) * 100) },
    { name: 'LSTM',             score: Math.round((data.lstm || 0) * 100) },
    { name: 'Graph NN',         score: Math.round((data.graph || 0) * 100) },
  ]

  return (
    <ResponsiveContainer width="100%" height={120}>
      <BarChart data={chartData} layout="vertical" margin={{ top: 0, right: 10, left: 10, bottom: 0 }}>
        <CartesianGrid strokeDasharray="3 3" stroke="#1e293b" horizontal={false} />
        <XAxis type="number" domain={[0, 100]} tick={{ fontSize: 10, fill: '#64748b' }} />
        <YAxis type="category" dataKey="name" tick={{ fontSize: 10, fill: '#94a3b8' }} width={100} />
        <Tooltip
          formatter={(v) => [`${v}%`, 'Avg Score']}
          contentStyle={{ background: '#0f172a', border: '1px solid #1e293b', borderRadius: 8, fontSize: 11 }}
        />
        <Bar dataKey="score" fill="#6366f1" radius={[0, 4, 4, 0]} />
      </BarChart>
    </ResponsiveContainer>
  )
}