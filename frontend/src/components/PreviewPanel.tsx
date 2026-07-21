import React, { useMemo, useState, useCallback, useRef, useEffect } from 'react'
import { AgGridReact } from 'ag-grid-react'
import 'ag-grid-community/styles/ag-grid.css'
import 'ag-grid-community/styles/ag-theme-quartz.css'
import { useStore } from '../store'

const DTYPE_LABELS: Record<string, string> = {
  numeric: 'Numérique', categorical: 'Catégoriel', datetime: 'Date', text: 'Texte',
}

function DTypeBadge({ dtype }: { dtype: string }) {
  return (
    <span className={`dtype-badge dtype--${dtype}`}>
      {DTYPE_LABELS[dtype] ?? dtype}
    </span>
  )
}

function StatPill({ label, value }: { label: string; value: string | number }) {
  return (
    <span className="badge badge--neutral" style={{ gap: 4 }}>
      <span style={{ color: 'var(--text-3)', fontSize: 11 }}>{label}</span>
      <span style={{ fontWeight: 600, color: 'var(--text-1)' }}>{value}</span>
    </span>
  )
}

export function PreviewPanel() {
  const { columns, previewRows, rowCount, fileName } = useStore()
  const wrapperRef = useRef<HTMLDivElement>(null)
  const [showFade, setShowFade] = useState(false)

  const checkScroll = useCallback(() => {
    if (!wrapperRef.current) return
    const viewport = wrapperRef.current.querySelector('.ag-body-viewport')
    if (viewport) {
      // Show fade if there's horizontal content we haven't scrolled to yet
      const isScrollableToRight = Math.ceil(viewport.scrollLeft + viewport.clientWidth) < viewport.scrollWidth - 2
      setShowFade(isScrollableToRight)
    }
  }, [])

  // Check on mount/resize (in case the grid container changes size)
  useEffect(() => {
    window.addEventListener('resize', checkScroll)
    return () => window.removeEventListener('resize', checkScroll)
  }, [checkScroll])

  const colDefs = useMemo(() => columns.map((col) => ({
    field: col.name,
    headerName: col.name,
    flex: 1,
    minWidth: 120,
    headerComponent: (props: any) => {
      let sortIcon = null
      if (props.sort === 'asc') sortIcon = '↑'
      else if (props.sort === 'desc') sortIcon = '↓'
      
      const onSortRequested = (event: any) => {
        if (props.progressSort) props.progressSort(event.shiftKey)
      }

      return (
        <div 
          onClick={onSortRequested} 
          style={{ 
            display: 'flex', flexDirection: 'column', alignItems: 'center', 
            justifyContent: 'center', width: '100%', cursor: 'pointer', padding: '4px 0',
            overflow: 'hidden'
          }}
          title={col.name}
        >
          <div style={{ display: 'flex', alignItems: 'center', gap: 4, maxWidth: '100%' }}>
            <span style={{ 
              fontWeight: 600, fontSize: 12, color: 'var(--text-1)', 
              whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' 
            }}>
              {col.name}
            </span>
            {sortIcon && <span style={{ fontSize: 12, color: 'var(--text-3)' }}>{sortIcon}</span>}
          </div>
          <DTypeBadge dtype={col.dtype} />
        </div>
      )
    },
    cellStyle: { fontSize: '13px', color: 'var(--text-1)' },
    valueFormatter: (p: any) => (p.value == null ? '—' : String(p.value)),
  })), [columns])

  if (!columns.length) return null

  return (
    <div className="preview-panel" id="preview-panel">
      {/* Section header */}
      <div className="section-header">
        <div className="section-icon" aria-hidden="true">
          <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
            <rect x="3" y="3" width="18" height="18" rx="2"/><line x1="3" y1="9" x2="21" y2="9"/>
            <line x1="3" y1="15" x2="21" y2="15"/><line x1="9" y1="3" x2="9" y2="21"/>
          </svg>
        </div>
        <div style={{ flex: 1 }}>
          <p className="section-header__title">Aperçu — {fileName}</p>
          <p className="section-header__sub">Premières lignes de votre fichier</p>
        </div>
        <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap' }}>
          <StatPill label="Lignes" value={(rowCount ?? 0).toLocaleString('fr-FR')} />
          <StatPill label="Colonnes" value={columns.length} />
        </div>
      </div>



      {/* Grid */}
      <div className="preview-panel__inner">
        <div className="preview-grid-wrapper" ref={wrapperRef}>
          <div className="ag-theme-quartz preview-grid">
            <AgGridReact
              rowData={previewRows}
              columnDefs={colDefs}
              domLayout="autoHeight"
              defaultColDef={{ resizable: true, sortable: true }}
              rowHeight={38}
              headerHeight={58}
              onGridReady={checkScroll}
              onGridSizeChanged={checkScroll}
              onBodyScroll={checkScroll}
            />
          </div>
          {showFade && <div className="preview-grid-fade" aria-hidden="true" />}
        </div>
      </div>
    </div>
  )
}
