import { ShieldAlert, ShieldX, Shield, Activity, Clock } from 'lucide-react'

const CARDS = [
  { key: 'critical',        label: 'Critical',       icon: ShieldX,     color: '#ef4444' },
  { key: 'high',            label: 'High',            icon: ShieldAlert, color: '#f97316' },
  { key: 'threats_last_24h',label: 'Last 24h',        icon: Clock,       color: '#a78bfa' },
  { key: 'open',            label: 'Open',            icon: Activity,    color: '#38bdf8' },
  { key: 'auto_contained',  label: 'Auto-Contained',  icon: Shield,      color: '#34d399' },
]

export default function MetricsBar({ stats }) {
  if (!stats) return null
  return (
    <div style={{ display: 'grid', gridTemplateColumns: 'repeat(5, 1fr)', gap: 12, marginBottom: 24 }}>
      {CARDS.map(({ key, label, icon: Icon, color }) => (
        <div key={key} style={{
          background: 'var(--card-bg)',
          border: '1px solid var(--border)',
          borderRadius: 10,
          padding: '14px 18px',
          display: 'flex',
          flexDirection: 'column',
          gap: 6,
        }}>
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
            <span style={{ fontSize: 12, color: 'var(--muted)', fontWeight: 500, textTransform: 'uppercase', letterSpacing: '0.05em' }}>{label}</span>
            <Icon size={14} color={color} />
          </div>
          <span style={{ fontSize: 28, fontWeight: 700, color, lineHeight: 1 }}>
            {(stats[key] ?? 0).toLocaleString()}
          </span>
        </div>
      ))}
    </div>
  )
}