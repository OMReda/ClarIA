import React, { useEffect, useState } from 'react'
import { fetchKPIAggregate } from '../api/client'
import { useStore } from '../store'
import { Euro, Percent, Hash, GripHorizontal } from 'lucide-react'

interface KPICardProps {
  id: string
  column: string
  aggregation: string
  label: string
  format?: 'number' | 'currency' | 'percent'
  onEdit: (id: string) => void
  onDelete: (id: string) => void
}

export function KPICard({ id, column, aggregation, label, format = 'number', onEdit, onDelete }: KPICardProps) {
  const fileId = useStore(s => s.fileId)
  const [value, setValue] = useState<number | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    if (!fileId) return
    
    let isMounted = true
    setLoading(true)
    setError(null)
    
    fetchKPIAggregate(fileId, column, aggregation)
      .then(res => {
        if (isMounted) {
          setValue(res.value)
          setLoading(false)
        }
      })
      .catch(err => {
        if (isMounted) {
          setError(err.message)
          setLoading(false)
        }
      })
      
    return () => { isMounted = false }
  }, [fileId, column, aggregation])

  const formattedValue = value !== null 
    ? format === 'currency' 
      ? new Intl.NumberFormat('fr-FR', { style: 'currency', currency: 'EUR', maximumFractionDigits: 0 }).format(value)
      : format === 'percent'
      ? new Intl.NumberFormat('fr-FR', { style: 'percent', maximumFractionDigits: 2 }).format(value / 100) // Assumes value is 0-100 based on standard CSVs
      : new Intl.NumberFormat('fr-FR', { maximumFractionDigits: 2 }).format(value)
    : '-'

  const Icon = format === 'currency' ? Euro : format === 'percent' ? Percent : Hash

  return (
    <div className="card dashboard-kpi-card animate-fade-up" style={{ flex: '0 0 auto', minWidth: 280, maxWidth: 380, height: 130, padding: '20px 24px', display: 'flex', flexDirection: 'column', position: 'relative', border: '1px solid var(--border)', borderRadius: 'var(--radius-xl)', background: 'linear-gradient(145deg, var(--bg-secondary) 0%, var(--surface) 100%)', boxShadow: '0 2px 8px rgba(0,0,0,0.02)', overflow: 'hidden', transition: 'box-shadow 0.3s ease, transform 0.3s ease' }}>
      
      <div className="kpi-card-bg-icon" style={{ position: 'absolute', right: -15, bottom: -20, opacity: 0.03, transform: 'rotate(-10deg)', pointerEvents: 'none', transition: 'transform 0.4s ease, opacity 0.4s ease' }}>
        <Icon size={140} strokeWidth={2} />
      </div>

      <div className="kpi-drag-handle" style={{ position: 'absolute', top: 6, left: '50%', transform: 'translateX(-50%)', opacity: 0, transition: 'opacity 0.2s', color: 'var(--text-tertiary)', pointerEvents: 'none' }}>
        <GripHorizontal size={16} />
      </div>

      {/* Header Row: Icon + Label + Actions */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', width: '100%', zIndex: 10 }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 10, overflow: 'hidden', flex: 1, paddingRight: 12 }}>
          <div style={{ width: 32, height: 32, borderRadius: 8, backgroundColor: 'var(--blue-light)', display: 'flex', alignItems: 'center', justifyContent: 'center', color: 'var(--blue)', flexShrink: 0 }}>
            <Icon size={16} strokeWidth={2.5} />
          </div>
          <div style={{ fontSize: '0.875rem', color: 'var(--text-secondary)', fontWeight: 600, display: '-webkit-box', WebkitLineClamp: 2, WebkitBoxOrient: 'vertical', overflow: 'hidden', textTransform: 'uppercase', letterSpacing: '0.05em', lineHeight: '1.2' }} title={label}>
            {label}
          </div>
        </div>

        <div className="kpi-card-actions" style={{ display: 'flex', gap: 4, flexShrink: 0, marginRight: -8, marginTop: -8 }}>
          <button onClick={() => onEdit(id)} className="btn btn--ghost btn--icon btn--sm" style={{ padding: 4 }} title="Modifier">
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M12 20h9"></path><path d="M16.5 3.5a2.121 2.121 0 0 1 3 3L7 19l-4 1 1-4L16.5 3.5z"></path></svg>
          </button>
          <button onClick={() => onDelete(id)} className="btn btn--ghost btn--icon btn--sm" style={{ padding: 4 }} title="Supprimer">
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><polyline points="3 6 5 6 21 6"></polyline><path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"></path></svg>
          </button>
        </div>
      </div>
      
      {/* Value Row */}
      <div style={{ flex: 1, display: 'flex', flexDirection: 'column', justifyContent: 'center', zIndex: 1, marginTop: 8 }}>
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
