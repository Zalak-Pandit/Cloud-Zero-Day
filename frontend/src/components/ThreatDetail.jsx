import { format } from 'date-fns'
import { X, ShieldCheck, AlertTriangle, Cpu, Network, FileCode } from 'lucide-react'
import { api } from '../api/client'

const SEV_COLOR = {
  critical: '#ef4444', high: '#f97316', medium: '#eab308', low: '#22c55e',
}

const MODEL_ICONS = {
  isolation_forest: Cpu,
  lstm:             Network,
  graph:            FileCode,
}
const MODEL_LABELS = {
  isolation_forest: 'Isolation Forest',
  lstm:             'LSTM Sequence',
  graph:            'Graph Neural Net',
}

function ScoreBar({ value, color }) {
  return (
    <div style={{ height: 6, background: 'var(--border)', borderRadius: 3, overflow: 'hidden', flex: 1 }}>
      <div style={{
        height: '100%', borderRadius: 3,
        width: `${Math.round(value * 100)}%`,
        background: color,
        transition: 'width 0.4s ease',
      }} />
    </div>
  )
}

export default function ThreatDetail({ threat, onClose, onStatusChange }) {
  if (!threat) return (
    <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center',
      height: '100%', color: 'var(--muted)', fontSize: 13, flexDirection: 'column', gap: 8 }}>
      <AlertTriangle size={28} color="var(--muted)" />
      Select a threat to view details
    </div>
  )

  const sev = threat.severity
  const sevColor = SEV_COLOR[sev] || '#94a3b8'
  const scores = threat.model_scores || {}

  async function handleStatusChange(status) {
    try {
      await api.threats.updateStatus(threat.id, status)
      onStatusChange?.()
    } catch (e) {
      console.error(e)
    }
  }

  return (
    <div style={{ height: '100%', overflowY: 'auto', padding: '0 2px' }}>
      {/* Header */}
      <div style={{ display: 'flex', alignItems: 'flex-start', justifyContent: 'space-between', marginBottom: 20 }}>
        <div>
          <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 4 }}>
            <span style={{
              fontSize: 10, fontWeight: 700, padding: '3px 8px', borderRadius: 4,
              background: sevColor + '22', color: sevColor, border: `1px solid ${sevColor}55`,
              textTransform: 'uppercase', letterSpacing: '0.06em',
            }}>
              {sev}
            </span>
            <span style={{ fontSize: 10, color: 'var(--muted)', fontFamily: 'monospace' }}>
              {threat.id?.slice(0, 8)}
            </span>
          </div>
          <div style={{ fontSize: 15, fontWeight: 700, color: 'var(--text)', marginBottom: 2 }}>
            {threat.threat_type?.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase())}
          </div>
          <div style={{ fontSize: 11, color: 'var(--muted)' }}>
            {threat.created_at ? format(new Date(threat.created_at), 'MMM d, yyyy HH:mm:ss') : ''}
          </div>
        </div>
        <button onClick={onClose} style={{
          background: 'none', border: 'none', cursor: 'pointer', color: 'var(--muted)', padding: 4
        }}>
          <X size={16} />
        </button>
      </div>

      {/* Description */}
      <div style={{
        background: 'var(--card-bg)', border: '1px solid var(--border)',
        borderRadius: 8, padding: '12px 14px', marginBottom: 16, fontSize: 12,
        color: 'var(--text)', lineHeight: 1.6,
      }}>
        {threat.description}
      </div>

      {/* Key info grid */}
      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 10, marginBottom: 16 }}>
        {[
          ['Source IP',    threat.source_ip || '—'],
          ['Target',       threat.target_resource || '—'],
          ['Region',       threat.region || '—'],
          ['Status',       threat.status || '—'],
          ['Confidence',   `${Math.round((threat.confidence_score || 0) * 100)}%`],
          ['Auto-Contained', threat.auto_contained ? 'Yes' : 'No'],
        ].map(([label, val]) => (
          <div key={label} style={{
            background: 'var(--card-bg)', border: '1px solid var(--border)',
            borderRadius: 8, padding: '10px 12px',
          }}>
            <div style={{ fontSize: 10, color: 'var(--muted)', marginBottom: 3, textTransform: 'uppercase', letterSpacing: '0.05em' }}>{label}</div>
            <div style={{ fontSize: 12, fontWeight: 600, color: 'var(--text)', fontFamily: typeof val === 'string' && val.includes('.') ? 'monospace' : 'inherit' }}>{val}</div>
          </div>
        ))}
      </div>

      {/* ML Model Scores */}
      <div style={{ marginBottom: 16 }}>
        <div style={{ fontSize: 11, fontWeight: 600, color: 'var(--muted)', marginBottom: 10,
          textTransform: 'uppercase', letterSpacing: '0.06em' }}>
          ML Model Scores
        </div>
        <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
          {Object.entries(scores).map(([model, score]) => {
            const Icon = MODEL_ICONS[model] || Cpu
            const pct = Math.round(score * 100)
            const color = pct >= 80 ? '#ef4444' : pct >= 60 ? '#f97316' : '#22c55e'
            return (
              <div key={model}>
                <div style={{ display: 'flex', alignItems: 'center', gap: 6, marginBottom: 4 }}>
                  <Icon size={12} color={color} />
                  <span style={{ fontSize: 11, color: 'var(--muted)', flex: 1 }}>{MODEL_LABELS[model] || model}</span>
                  <span style={{ fontSize: 11, fontWeight: 700, color, fontFamily: 'monospace' }}>{pct}%</span>
                </div>
                <ScoreBar value={score} color={color} />
              </div>
            )
          })}
        </div>
      </div>

      {/* Indicators */}
      {threat.indicators?.length > 0 && (
        <div style={{ marginBottom: 16 }}>
          <div style={{ fontSize: 11, fontWeight: 600, color: 'var(--muted)', marginBottom: 8,
            textTransform: 'uppercase', letterSpacing: '0.06em' }}>Indicators</div>
          <div style={{ display: 'flex', flexWrap: 'wrap', gap: 6 }}>
            {threat.indicators.map(ind => (
              <span key={ind} style={{
                fontSize: 11, padding: '3px 8px', borderRadius: 4,
                background: '#1e1b4b', color: '#a5b4fc', border: '1px solid #3730a3',
              }}>{ind.replace(/_/g, ' ')}</span>
            ))}
          </div>
        </div>
      )}

      {/* Status actions */}
      <div>
        <div style={{ fontSize: 11, fontWeight: 600, color: 'var(--muted)', marginBottom: 8,
          textTransform: 'uppercase', letterSpacing: '0.06em' }}>Update Status</div>
        <div style={{ display: 'flex', gap: 6 }}>
          {['investigating', 'contained', 'resolved'].map(s => (
            <button key={s} onClick={() => handleStatusChange(s)} style={{
              flex: 1, padding: '7px 0', fontSize: 11, fontWeight: 600,
              borderRadius: 6, cursor: 'pointer', border: '1px solid var(--border)',
              background: threat.status === s ? 'var(--accent)' : 'var(--card-bg)',
              color: threat.status === s ? '#fff' : 'var(--muted)',
              textTransform: 'capitalize', transition: 'all 0.15s',
            }}>
              {s}
            </button>
          ))}
        </div>
      </div>
    </div>
  )
}