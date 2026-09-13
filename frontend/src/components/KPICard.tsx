import React, { useEffect, useState } from 'react'
import { fetchKPIAggregate } from '../api/client'
import { useStore } from '../store'
import type { KPIFilter } from '../store'
import { Euro, Percent, Hash, GripHorizontal } from 'lucide-react'

interface KPICardProps {
  id: string
  column: string
  aggregation: string
  label: string
  format?: 'number' | 'currency' | 'percent'
  filters?: KPIFilter[]
  onEdit: (id: string) => void
  onDelete: (id: string) => void
}

// Operator display labels for filter badges on the card
const OP_LABELS: Record<string, string> = {
  eq: '=', ne: '≠', gt: '>', gte: '≥', lt: '<', lte: '≤', contains: 'contient',
}

export function KPICard({ id, column, aggregation, label, format = 'number', filters = [], onEdit, onDelete }: KPICardProps) {
  const fileId = useStore(s => s.fileId)

  const [value, setValue] = useState<number | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  // Re-fetch whenever the file, column, aggregation or filters change
  useEffect(() => {
    if (!fileId) return
    let isMounted = true
    setLoading(true)
    setError(null)
    fetchKPIAggregate(fileId, column, aggregation, filters.length > 0 ? filters : undefined)
      .then(res => { if (isMounted) { setValue(res.value); setLoading(false) } })
      .catch(err => { if (isMounted) { setError(err.message); setLoading(false) } })
    return () => { isMounted = false }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [fileId, column, aggregation, JSON.stringify(filters)])

  const formattedValue = value !== null
    ? format === 'currency'
      ? new Intl.NumberFormat('fr-FR', { style: 'currency', currency: 'EUR', maximumFractionDigits: 0 }).format(value)
      : format === 'percent'
      ? new Intl.NumberFormat('fr-FR', { style: 'percent', maximumFractionDigits: 2 }).format(value / 100)
      : new Intl.NumberFormat('fr-FR', { maximumFractionDigits: 2 }).format(value)
    : '-'

  const Icon = format === 'currency' ? Euro : format === 'percent' ? Percent : Hash
  const hasFilters = filters.length > 0

  return (
    <div
      className="card dashboard-kpi-card animate-fade-up"
      style={{
        flex: '0 0 auto',
        minWidth: 280,
        maxWidth: 380,
        padding: '20px 24px',
        display: 'flex',
        flexDirection: 'column',
        position: 'relative',
        border: `1px solid ${hasFilters ? 'var(--blue)' : 'var(--border)'}`,
        borderRadius: 'var(--radius-xl)',
        background: 'linear-gradient(145deg, var(--bg-secondary) 0%, var(--surface) 100%)',
        boxShadow: hasFilters ? '0 2px 12px rgba(59,130,246,0.12)' : '0 2px 8px rgba(0,0,0,0.02)',
        overflow: 'visible',
        transition: 'box-shadow 0.3s ease, transform 0.3s ease',
      }}
    >
      {/* Background watermark icon */}
      <div style={{ position: 'absolute', right: -15, bottom: -20, opacity: 0.03, transform: 'rotate(-10deg)', pointerEvents: 'none' }}>
        <Icon size={140} strokeWidth={2} />
      </div>

      {/* Drag handle */}
      <div className="kpi-drag-handle" style={{ position: 'absolute', top: 6, left: '50%', transform: 'translateX(-50%)', opacity: 0, transition: 'opacity 0.2s', color: 'var(--text-tertiary)', pointerEvents: 'none' }}>
        <GripHorizontal size={16} />
      </div>

      {/* Header: icon + label + actions */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', width: '100%', zIndex: 10 }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 10, overflow: 'hidden', flex: 1, paddingRight: 4 }}>
          <div style={{
            width: 32, height: 32, borderRadius: 8,
            backgroundColor: hasFilters ? 'rgba(59,130,246,0.12)' : 'var(--blue-light)',
            display: 'flex', alignItems: 'center', justifyContent: 'center', color: 'var(--blue)', flexShrink: 0,
          }}>
            <Icon size={16} strokeWidth={2.5} />
          </div>
          <div style={{
            fontSize: '0.875rem', color: 'var(--text-secondary)', fontWeight: 600,
            display: '-webkit-box', WebkitLineClamp: 2, WebkitBoxOrient: 'vertical',
            overflow: 'hidden', textTransform: 'uppercase', letterSpacing: '0.05em', lineHeight: '1.2',
          }} title={label}>
            {label}
          </div>
        </div>

        {/* Action buttons */}
        <div className="kpi-card-actions" style={{ display: 'flex', gap: 2, flexShrink: 0, marginRight: -8, marginTop: -8 }}>
          <button onClick={() => onEdit(id)} className="btn btn--ghost btn--icon btn--sm" style={{ padding: 4 }} title="Modifier">
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
              <path d="M12 20h9"></path><path d="M16.5 3.5a2.121 2.121 0 0 1 3 3L7 19l-4 1 1-4L16.5 3.5z"></path>
            </svg>
          </button>
          <button onClick={() => onDelete(id)} className="btn btn--ghost btn--icon btn--sm" style={{ padding: 4 }} title="Supprimer">
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
              <polyline points="3 6 5 6 21 6"></polyline>
              <path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"></path>
            </svg>
          </button>
        </div>
      </div>

      {/* Active filter badges — read-only, shows what filters are active */}
      {hasFilters && (
        <div style={{ display: 'flex', flexWrap: 'wrap', gap: 4, marginTop: 8 }}>
          {filters.map((f, i) => (
            <span key={i} style={{
              display: 'inline-flex', alignItems: 'center', gap: 3,
              fontSize: 10, fontWeight: 600, padding: '2px 7px',
              borderRadius: 20, background: 'rgba(59,130,246,0.1)',
              color: 'var(--blue)', border: '1px solid rgba(59,130,246,0.2)',
              whiteSpace: 'nowrap', maxWidth: 180, overflow: 'hidden', textOverflow: 'ellipsis',
            }} title={`${f.column} ${OP_LABELS[f.operator] ?? f.operator} ${f.value}`}>
              {f.column} {OP_LABELS[f.operator] ?? f.operator} {f.value}
            </span>
          ))}
        </div>
      )}

      {/* KPI value */}
      <div style={{ flex: 1, display: 'flex', flexDirection: 'column', justifyContent: 'center', zIndex: 1, marginTop: 10 }}>
        {loading ? (
          <div style={{ width: '60%', height: 36, backgroundColor: 'var(--border)', borderRadius: 4, animation: 'pulse 2s cubic-bezier(0.4, 0, 0.6, 1) infinite' }} />
        ) : error ? (
          <div style={{ color: 'var(--danger)', fontSize: 13, fontWeight: 500 }}>{error}</div>
        ) : (
          <div style={{ fontSize: '2.5rem', lineHeight: '1', fontWeight: 700, color: 'var(--text-primary)', textShadow: '0 1px 2px rgba(0,0,0,0.05)' }}>
            {formattedValue}
          </div>
        )}
      </div>
    </div>
  )
}
