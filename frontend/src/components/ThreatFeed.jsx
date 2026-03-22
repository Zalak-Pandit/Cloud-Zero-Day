import { useState } from 'react'
import { formatDistanceToNow } from 'date-fns'
import { ChevronRight } from 'lucide-react'

const SEV_COLOR = {
  critical: { bg: '#450a0a', text: '#fca5a5', border: '#7f1d1d' },
  high:     { bg: '#431407', text: '#fdba74', border: '#7c2d12' },
  medium:   { bg: '#3b2f00', text: '#fde047', border: '#713f12' },
  low:      { bg: '#052e16', text: '#86efac', border: '#14532d' },
}

const TYPE_LABELS = {
  zero_day_exploit:       'Zero-Day Exploit',
  lateral_movement:       'Lateral Movement',
  privilege_escalation:   'Privilege Escalation',
  data_exfiltration:      'Data Exfiltration',
  command_injection:      'Command Injection',
  unusual_api_pattern:    'Unusual API Pattern',
  memory_corruption:      'Memory Corruption',
  anomalous_behavior:     'Anomalous Behavior',
}

export default function ThreatFeed({ threats, onSelect, selected }) {
  const [filter, setFilter] = useState('all')

  const visible = filter === 'all'
    ? threats
    : threats.filter(t => t.severity === filter)

  return (
    <div style={{ display: 'flex', flexDirection: 'column', height: '100%' }}>
      {/* Filter tabs */}
      <div style={{ display: 'flex', gap: 6, marginBottom: 12 }}>
        {['all', 'critical', 'high', 'medium', 'low'].map(f => (
          <button key={f} onClick={() => setFilter(f)} style={{
            padding: '4px 10px', borderRadius: 6, fontSize: 11, fontWeight: 600,
            border: '1px solid',
            textTransform: 'capitalize',
            cursor: 'pointer',
            background: filter === f ? (SEV_COLOR[f]?.bg || '#1e293b') : 'transparent',
            color:      filter === f ? (SEV_COLOR[f]?.text || '#e2e8f0') : 'var(--muted)',
            borderColor: filter === f ? (SEV_COLOR[f]?.border || '#334155') : 'var(--border)',
            transition: 'all 0.15s',
          }}>
            {f}
          </button>
        ))}
      </div>

      {/* Feed list */}
      <div style={{ flex: 1, overflowY: 'auto', display: 'flex', flexDirection: 'column', gap: 6 }}>
        {visible.length === 0 && (
          <div style={{ textAlign: 'center', color: 'var(--muted)', padding: '40px 0', fontSize: 13 }}>
            No threats detected
          </div>
        )}
        {visible.map(t => {
          const c = SEV_COLOR[t.severity] || SEV_COLOR.low
          const isSelected = selected?.id === t.id
          return (
            <div
              key={t.id}
              onClick={() => onSelect(t)}
              style={{
                background: isSelected ? 'var(--card-hover)' : 'var(--card-bg)',
                border: `1px solid ${isSelected ? c.border : 'var(--border)'}`,
                borderLeft: `3px solid ${c.text}`,
                borderRadius: 8,
                padding: '10px 12px',
                cursor: 'pointer',
                display: 'flex',
                alignItems: 'center',
                gap: 10,
                transition: 'all 0.12s',
              }}
            >
              {/* Severity badge */}
              <span style={{
                fontSize: 10, fontWeight: 700, padding: '2px 6px', borderRadius: 4,
                background: c.bg, color: c.text, border: `1px solid ${c.border}`,
                minWidth: 52, textAlign: 'center', textTransform: 'uppercase',
              }}>
                {t.severity}
              </span>

              {/* Main info */}
              <div style={{ flex: 1, minWidth: 0 }}>
                <div style={{ fontSize: 12, fontWeight: 600, color: 'var(--text)', marginBottom: 2,
                  whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>
                  {TYPE_LABELS[t.threat_type] || t.threat_type}
                </div>
                <div style={{ fontSize: 11, color: 'var(--muted)', display: 'flex', gap: 8 }}>
                  <span>{t.source_ip || '—'}</span>
                  <span style={{ color: 'var(--border)' }}>•</span>
                  <span>{Math.round((t.confidence_score || 0) * 100)}% conf</span>
                </div>
              </div>

              {/* Timestamp */}
              <div style={{ fontSize: 10, color: 'var(--muted)', whiteSpace: 'nowrap' }}>
                {t.created_at ? formatDistanceToNow(new Date(t.created_at), { addSuffix: true }) : ''}
              </div>

              <ChevronRight size={12} color="var(--muted)" />
            </div>
          )
        })}
      </div>
    </div>
  )
}