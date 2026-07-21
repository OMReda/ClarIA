/**
 * DashboardPage.tsx — Manual chart builder.
 *
 * Features:
 *  - Chart types: bar, line, area, pie, scatter
 *  - X / Y / Name / Value axis selectors driven by dataset columns
 *  - Chart title + optional aggregation toggle
 *  - Export PNG (ECharts getDataURL) and CSV (selected columns)
 *  - Fully client-side — no backend calls
 */
import React, { useRef, useState, useMemo, useEffect } from 'react'
import ReactECharts from 'echarts-for-react'
import { useDatasetStore } from '../store/datasetStore'
import type { Dataset } from '../store/datasetStore'
import { useStore } from '../store'
import { DashboardView } from '../components/DashboardView'
import { KPICard } from '../components/KPICard'
import { IconBarChart, IconFile } from '../components/Icon'
import { BarChart, LineChart, AreaChart, PieChart, Activity, BarChart2, Target, Grid, Sparkles, Plus, Trash2, AlertTriangle, Hash, Euro, Percent } from 'lucide-react'

interface FilterRule {
  column: string
  operator: '=' | 'contains' | '>' | '<'
  value: string
}
import { exportPNG, exportCSV, exportExcel, exportPowerBI } from '../utils/exportUtils'

// ── Color palettes ─────────────────────────────────────────────────────────
const PALETTES: { label: string; colors: string[] }[] = [
  { label: 'Bleu', colors: ['#2563eb', '#7c3aed', '#0891b2', '#059669', '#d97706', '#dc2626'] },
  { label: 'Sunset', colors: ['#f97316', '#ef4444', '#ec4899', '#a855f7', '#6366f1', '#14b8a6'] },
  { label: 'Foret', colors: ['#16a34a', '#15803d', '#166534', '#4ade80', '#86efac', '#bbf7d0'] },
  { label: 'Marine', colors: ['#0ea5e9', '#38bdf8', '#7dd3fc', '#0369a1', '#1d4ed8', '#6366f1'] },
  { label: 'Mono', colors: ['#1e293b', '#334155', '#475569', '#64748b', '#94a3b8', '#cbd5e1'] },
]

// ── Chart type definitions ─────────────────────────────────────────────────

type ChartType = 'bar' | 'line' | 'area' | 'pie' | 'scatter' | 'histogram' | 'radar' | 'heatmap'

const CHART_TYPES: { value: ChartType; label: string; icon: React.ReactNode }[] = [
  { value: 'bar', label: 'Barres', icon: <BarChart size={18} strokeWidth={1.75} /> },
  { value: 'line', label: 'Courbe', icon: <LineChart size={18} strokeWidth={1.75} /> },
  { value: 'area', label: 'Aire', icon: <AreaChart size={18} strokeWidth={1.75} /> },
  { value: 'pie', label: 'Camembert', icon: <PieChart size={18} strokeWidth={1.75} /> },
  { value: 'scatter', label: 'Nuage', icon: <Activity size={18} strokeWidth={1.75} /> },
  { value: 'histogram', label: 'Histogramme', icon: <BarChart2 size={18} strokeWidth={1.75} /> },
  { value: 'radar', label: 'Radar', icon: <Target size={18} strokeWidth={1.75} /> },
  { value: 'heatmap', label: 'Heatmap', icon: <Grid size={18} strokeWidth={1.75} /> },
]

// ── ECharts option builder ─────────────────────────────────────────────────

function getAggregatedValue(vals: number[], aggregation: string): number {
  if (vals.length === 0) return 0;
  switch (aggregation) {
    case 'count': return vals.length;
    case 'avg': return vals.reduce((a, b) => a + b, 0) / vals.length;
    case 'min': return Math.min(...vals);
    case 'max': return Math.max(...vals);
    case 'sum':
    default:
      return vals.reduce((a, b) => a + b, 0);
  }
}

function buildOption(
  type: ChartType,
  rows: Record<string, unknown>[],
  xCol: string,
  yCol: string,
  title: string,
  palette: string[],
  smooth: boolean,
  aggregation: string = 'sum'
) {
  const base = {
    animation: true,
    // Always suppress in-canvas title — the card header renders it
    title: { text: title || '', show: false },
    tooltip: { trigger: (type === 'pie' || type === 'radar') ? 'item' : 'axis', confine: true },
    grid: { left: 60, right: 20, top: 20, bottom: 45, containLabel: true },
    color: palette,
  }

  if (type === 'pie') {
    const aggGroup: Record<string, number[]> = {}
    rows.forEach((r) => {
      const k = String(r[xCol] ?? '(vide)')
      const v = Number(r[yCol]) || 0
      if (!aggGroup[k]) aggGroup[k] = []
      aggGroup[k].push(v)
    })
    return {
      ...base,
      tooltip: { trigger: 'item', formatter: '{b}: {c} ({d}%)' },
      series: [{
        type: 'pie', radius: ['35%', '65%'], center: ['50%', '50%'],
        data: Object.entries(aggGroup).map(([name, vals]) => ({
          name,
          value: getAggregatedValue(vals, aggregation)
        })),
        label: { fontSize: 12 },
        emphasis: { itemStyle: { shadowBlur: 10, shadowOffsetX: 0, shadowColor: 'rgba(0,0,0,0.18)' } },
      }],
    }
  }

  if (type === 'scatter') {
    return {
      ...base,
      xAxis: { type: 'value', name: xCol, nameLocation: 'middle', nameGap: 30 },
      yAxis: { type: 'value', name: yCol, nameLocation: 'middle', nameGap: 40 },
      series: [{ type: 'scatter', data: rows.map((r) => [Number(r[xCol]) || 0, Number(r[yCol]) || 0]), symbolSize: 8, itemStyle: { opacity: 0.75 } }],
    }
  }

  if (type === 'histogram') {
    const vals = rows.map(r => Number(r[xCol])).filter(n => !isNaN(n))
    if (vals.length === 0) return { ...base, xAxis: { type: 'value' }, yAxis: { type: 'value' }, series: [] }
    const min = Math.min(...vals), max = Math.max(...vals)
    const binCount = 20
    const binSize = (max - min) / binCount || 1
    const bins = Array(binCount).fill(0)
    vals.forEach(v => {
      let idx = Math.floor((v - min) / binSize)
      if (idx >= binCount) idx = binCount - 1
      bins[idx]++
    })
    const xData = Array.from({ length: binCount }, (_, i) => (min + i * binSize).toFixed(1))
    return {
      ...base,
      xAxis: { type: 'category', data: xData, name: xCol, nameLocation: 'middle', nameGap: 36, axisLabel: { rotate: 45 } },
      yAxis: { type: 'value', name: 'Fréquence' },
      series: [{ type: 'bar', data: bins, barCategoryGap: 0, itemStyle: { borderRadius: [4, 4, 0, 0] } }],
    }
  }

  // Radar (needs indicators + single series to match the UI's X/Y selectors)
  if (type === 'radar') {
    const aggGroup: Record<string, number[]> = {}

    rows.forEach(r => {
      const ind = String(r[xCol] ?? 'Ind')
      const val = Number(r[yCol]) || 0
      if (!aggGroup[ind]) aggGroup[ind] = []
      aggGroup[ind].push(val)
    })

    const indArray = Object.keys(aggGroup).slice(0, 8)

    // ECharts radar charts look broken (like a single stick) if there are less than 3 axes.
    // Pad the axes to at least 3 to maintain the spider-web shape.
    const paddedIndArray = [...indArray]
    while (paddedIndArray.length > 0 && paddedIndArray.length < 3) {
      paddedIndArray.push(`(vide ${paddedIndArray.length + 1})`)
    }

    const data = [{
      name: yCol,
      value: paddedIndArray.map(ind => aggGroup[ind] ? getAggregatedValue(aggGroup[ind], aggregation) : 0)
    }]

    return {
      ...base,
      radar: { indicator: paddedIndArray.length ? paddedIndArray.map(text => ({ text })) : [{ text: 'N/A' }] },
      series: [{
        type: 'radar',
        data,
        areaStyle: { opacity: 0.25 },
        itemStyle: { borderWidth: 2 }
      }]
    }
  }

  // Heatmap (X, Y, Val)
  if (type === 'heatmap') {
    const xVals = Array.from(new Set(rows.map(r => String(r[xCol] ?? 'X')))).slice(0, 20)
    const yVals = Array.from(new Set(rows.map(r => String(r[yCol] ?? 'Y')))).slice(0, 10)

    // Default val column is the first numeric that isn't X or Y
    const valCol = Object.keys(rows[0] || {}).find(k => k !== xCol && k !== yCol && typeof rows[0][k] === 'number')

    const aggGroup: Record<string, number[]> = {}
    rows.forEach(r => {
      const xIdx = xVals.indexOf(String(r[xCol]))
      const yIdx = yVals.indexOf(String(r[yCol]))
      const val = valCol ? Number(r[valCol]) || 0 : 1
      if (xIdx !== -1 && yIdx !== -1) {
        const k = `${xIdx},${yIdx}`
        if (!aggGroup[k]) aggGroup[k] = []
        aggGroup[k].push(val)
      }
    })

    const data: [number, number, number][] = []
    let maxVal = 0
    for (const [k, vals] of Object.entries(aggGroup)) {
      const [x, y] = k.split(',').map(Number)
      const aggVal = getAggregatedValue(vals, aggregation)
      data.push([x, y, aggVal])
      if (aggVal > maxVal) maxVal = aggVal
    }

    return {
      ...base,
      grid: { left: 60, right: 20, bottom: 60, top: 20 },
      xAxis: { type: 'category', data: xVals, splitArea: { show: true } },
      yAxis: { type: 'category', data: Array.from({ length: yVals.length }, (_, i) => yVals[i]), splitArea: { show: true } },
      visualMap: {
        min: 0, max: maxVal, calculable: true, orient: 'vertical', right: 0, top: 'center',
        inRange: { color: [palette[4] || '#e2e8f0', palette[0] || '#2563eb'] }
      },
      series: [{ type: 'heatmap', data, label: { show: false } }],
    }
  }

  // Bar / Line / Area
  const aggGroup: Record<string, number[]> = {}
  const order: string[] = []
  rows.forEach((r) => {
    const k = String(r[xCol] ?? '(vide)')
    const v = Number(r[yCol]) || 0
    if (!(k in aggGroup)) {
      order.push(k)
      aggGroup[k] = []
    }
    aggGroup[k].push(v)
  })

  const xData = order.slice(0, 80)
  const yData = xData.map((k) => getAggregatedValue(aggGroup[k], aggregation))

  return {
    ...base,
    xAxis: { type: 'category', data: xData, name: xCol, nameLocation: 'middle', nameGap: 36, axisLabel: { rotate: xData.length > 12 ? 35 : 0, fontSize: 11, color: '#475569' } },
    yAxis: { type: 'value', name: yCol, nameLocation: 'middle', nameGap: 50, axisLabel: { color: '#475569' } },
    series: [{
      type: type === 'area' ? 'line' : type, data: yData,
      smooth: smooth && (type === 'line' || type === 'area'),
      areaStyle: type === 'area' ? { opacity: 0.18 } : undefined,
      barMaxWidth: 56, itemStyle: { borderRadius: type === 'bar' ? [4, 4, 0, 0] : 0 }
    }],
  }
}

// ── Helpers ────────────────────────────────────────────────────────────────

// ── Column selector ────────────────────────────────────────────────────────

function ColSelect({
  id, label, value, onChange, columns, filter,
}: {
  id: string
  label: string
  value: string
  onChange: (v: string) => void
  columns: { name: string; dtype: string }[]
  filter?: (c: { name: string; dtype: string }) => boolean
}) {
  const opts = filter ? columns.filter(filter) : columns
  return (
    <div className="db-field">
      <label htmlFor={id} className="db-label">{label}</label>
      <select
        id={id}
        className="db-select"
        value={value}
        onChange={(e) => onChange(e.target.value)}
      >
        <option value="">— Choisir —</option>
        {opts.map((c) => (
          <option key={c.name} value={c.name}>{c.name}</option>
        ))}
      </select>
    </div>
  )
}

// ── Chart type button ──────────────────────────────────────────────────────

function ChartTypeBtn({
  ct, active, onClick,
}: { ct: typeof CHART_TYPES[0]; active: boolean; onClick: () => void }) {
  return (
    <button
      id={`chart-type-${ct.value}`}
      className={`chart-type-btn${active ? ' chart-type-btn--active' : ''}`}
      onClick={onClick}
      aria-pressed={active}
      title={ct.label}
    >
      <span className="chart-type-btn__icon">{ct.icon}</span>
      <span className="chart-type-btn__label">{ct.label}</span>
    </button>
  )
}

// ── Main component ─────────────────────────────────────────────────────────

function Builder({
  ds, initialConfig, editingChartId, builderType, onSave, onCancel,
}: {
  ds: Dataset
  initialConfig?: { chartType?: ChartType; xCol?: string; yCol?: string; title?: string; paletteIdx?: number; smooth?: boolean; aggregation?: 'sum' | 'avg' | 'count' | 'min' | 'max'; filters?: FilterRule[]; isAiGenerated?: boolean; rawSpec?: any }
  editingChartId: string | null
  builderType: 'chart' | 'kpi'
  onSave: (c: any) => void
  onCancel: () => void
}) {
  const chartRef = useRef<ReactECharts>(null)

  // Initialize chartType safely for Aski graphs
  const initialChartType = (() => {
    if (initialConfig?.isAiGenerated && initialConfig?.rawSpec?.series?.[0]) {
      const s = initialConfig.rawSpec.series[0]
      if (s.type === 'line' && s.areaStyle) return 'area'
      if (s.type === 'bar' && s.itemStyle?.borderRadius) return 'bar' // or histogram, but bar is safer
      return (s.type as ChartType) || 'bar'
    }
    return initialConfig?.chartType || 'bar'
  })();

  const [chartType, setChartType] = useState<ChartType>(initialChartType)
  const [xCol, setXCol] = useState(initialConfig?.xCol || '')
  const [yCol, setYCol] = useState(initialConfig?.yCol || '')
  const [title, setTitle] = useState(initialConfig?.title || '')
  const [paletteIdx, setPaletteIdx] = useState(initialConfig?.paletteIdx ?? (initialConfig?.isAiGenerated ? -1 : 0))
  const [smooth, setSmooth] = useState(initialConfig?.smooth ?? (() => {
    if (initialConfig?.isAiGenerated && initialConfig?.rawSpec?.series?.[0]) {
      return !!initialConfig.rawSpec.series[0].smooth
    }
    return false
  })())

  const [filters, setFilters] = useState<FilterRule[]>(initialConfig?.filters || [])

  const cols = ds.columns
  const rowsRaw = ds.fullData || ds.previewRows
  const numCols = cols.filter((c) => c.dtype === 'numeric')
  const anyCols = cols

  const rows = useMemo(() => {
    if (filters.length === 0) return rowsRaw
    return rowsRaw.filter(r => {
      for (const f of filters) {
        if (!f.column || !f.operator || f.value === '') continue
        const val = r[f.column]
        if (val === null || val === undefined) return false

        if (f.operator === '=') {
          if (String(val).toLowerCase() !== String(f.value).toLowerCase()) return false
        } else if (f.operator === 'contains') {
          if (!String(val).toLowerCase().includes(String(f.value).toLowerCase())) return false
        } else if (f.operator === '>') {
          if (Number(val) <= Number(f.value)) return false
        } else if (f.operator === '<') {
          if (Number(val) >= Number(f.value)) return false
        }
      }
      return true
    })
  }, [rowsRaw, filters])

  const [aggregation, setAggregation] = useState<'sum' | 'avg' | 'count' | 'min' | 'max'>(() => {
    if (initialConfig?.aggregation) return initialConfig.aggregation

    // Smart default based on yCol
    const yColName = (initialConfig?.yCol || '').toLowerCase()
    if (yColName.includes('id') || yColName.includes('count') || yColName.includes('nb') || yColName.includes('nombre')) {
      return 'count'
    }
    return 'sum'
  })

  const [format, setFormat] = useState<'number' | 'currency' | 'percent'>(() => {
    // We can extract this if we pass it, but for now default to 'number'
    return 'number'
  })

  // Auto-fill KPI title if it's empty
  useEffect(() => {
    if (builderType === 'kpi' && xCol && !editingChartId) {
      const aggNames = { sum: 'Somme', avg: 'Moyenne', count: 'Nombre', min: 'Minimum', max: 'Maximum' }
      const newTitle = `${aggNames[aggregation]} de ${xCol}`

      setTitle(prev => {
        if (!prev) return newTitle
        // If they already have an auto-generated title, update it
        const wasAutoGenerated = Object.values(aggNames).some(agg => prev.startsWith(agg + ' de '))
        if (wasAutoGenerated) return newTitle
        return prev
      })
    }
  }, [xCol, aggregation, builderType, editingChartId])

  const isAiGenerated = initialConfig?.isAiGenerated ?? false

  const isAiCartesian = isAiGenerated && (initialConfig?.rawSpec?.xAxis || initialConfig?.rawSpec?.yAxis)
  const allowedChartTypes = useMemo(() => {
    if (!isAiGenerated) return CHART_TYPES
    if (isAiCartesian) {
      return CHART_TYPES.filter(ct => ['bar', 'line', 'area', 'histogram'].includes(ct.value))
    }
    return CHART_TYPES.filter(ct => ct.value === initialChartType)
  }, [isAiGenerated, isAiCartesian, initialChartType])

  // For histogram, only xCol is needed — yCol auto-set to sentinel so canRender works
  const effectiveYCol = chartType === 'histogram' ? (xCol ? '_hist' : '') : yCol
  const canRender = builderType === 'kpi' ? !!(xCol && title && aggregation) : (isAiGenerated ? !!initialConfig?.rawSpec : !!(xCol && effectiveYCol && rows.length > 0))
  const palette = paletteIdx === -1 ? [] : PALETTES[paletteIdx].colors

  const option = useMemo(() => {
    if (builderType === 'kpi') return null
    if (isAiGenerated && initialConfig?.rawSpec) {
      const raw = initialConfig.rawSpec

      // Ensure boundaryGap is true for bar charts so bars don't clip the Y-axis
      const isBarLike = chartType === 'bar' || chartType === 'histogram'
      let xAxis = raw.xAxis
      if (isBarLike && xAxis) {
        if (Array.isArray(xAxis)) {
          xAxis = xAxis.map((x: any) => ({ ...x, boundaryGap: true }))
        } else {
          xAxis = { ...xAxis, boundaryGap: true }
        }
      }

      return {
        ...raw,
        ...(xAxis ? { xAxis } : {}),
        title: { ...(raw.title || {}), text: title },
        ...(paletteIdx !== -1 ? { color: palette } : {}),
        series: Array.isArray(raw.series) ? raw.series.map((s: any) => {
          const mappedType = chartType === 'area' ? 'line' : (chartType === 'histogram' ? 'bar' : chartType)
          const newS = {
            ...s,
            type: mappedType,
            smooth: smooth,
            itemStyle: { ...(s.itemStyle || {}), borderRadius: chartType === 'bar' || chartType === 'histogram' ? [4, 4, 0, 0] : (s.itemStyle?.borderRadius || 0) }
          }
          if (chartType === 'area') {
            newS.areaStyle = s.areaStyle || { opacity: 0.18 }
          } else {
            delete newS.areaStyle
          }
          return newS
        }) : raw.series
      }
    }
    if (!canRender) return null
    return buildOption(chartType, rows, xCol, effectiveYCol, title, palette, smooth, aggregation)
  }, [chartType, xCol, effectiveYCol, title, palette, smooth, aggregation, rows, canRender, isAiGenerated, initialConfig, builderType])

  const kpiPreviewValue = useMemo(() => {
    if (builderType !== 'kpi' || !xCol) return null

    let rawVals = rows.map(r => r[xCol]).filter(v => v !== null && v !== undefined)

    if (aggregation === 'count') {
      return rawVals.length
    }

    const numVals: number[] = rawVals.map(Number).filter(v => !isNaN(v))
    if (numVals.length === 0) return 0

    if (aggregation === 'sum') return numVals.reduce((a, b) => a + b, 0)
    if (aggregation === 'avg') return numVals.reduce((a, b) => a + b, 0) / numVals.length
    if (aggregation === 'min') return Math.min(...numVals)
    if (aggregation === 'max') return Math.max(...numVals)

    return 0
  }, [rows, xCol, aggregation, builderType])

  const handleExportPNG = () => {
    exportPNG(chartRef, `${ds.name}-chart.png`)
  }

  const handleExportCSV = () => {
    const selectedCols = [...new Set([xCol, yCol].filter(Boolean))]
    exportCSV(rows, selectedCols, `${ds.name}-export.csv`)
  }

  const handleExportExcel = () => {
    const selectedCols = [...new Set([xCol, yCol].filter(Boolean))]
    exportExcel(rows, selectedCols, `${ds.name}-excel.xlsx`)
  }

  const handleExportPowerBI = () => {
    const selectedCols = [...new Set([xCol, yCol].filter(Boolean))]
    exportPowerBI(rows, selectedCols, `${ds.name}-powerbi.xlsx`)
  }

  return (
    <div className="dashboard-builder">

      {/* ── Controls sidebar ── */}
      <aside className="dashboard-controls card" aria-label="Paramètres du graphique">

        {/* Header row */}
        <div className="db-section" style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 0 }}>
          <button className="btn btn--ghost btn--sm" onClick={onCancel}>← Retour</button>
          <span style={{ fontSize: 13, fontWeight: 600, color: 'var(--text-2)' }}>
            {editingChartId ? 'Modifier le graphique' : 'Nouveau graphique'}
          </span>
        </div>

        <hr className="divider" style={{ margin: 'var(--space-4) 0' }} />

        {builderType === 'kpi' ? (
          <>
            <div className="db-section">
              <p className="db-section-title">Indicateur clé (KPI)</p>

              <ColSelect id="kpi-col-select" label="Colonne de calcul" value={xCol} onChange={setXCol} columns={cols} filter={(c) => aggregation === 'count' || c.dtype === 'numeric'} />

              <div className="db-field" style={{ marginTop: 'var(--space-4)' }}>
                <label htmlFor="kpi-aggregation-select" className="db-label">Opération</label>
                <select id="kpi-aggregation-select" className="db-select" value={aggregation} onChange={(e) => {
                  const newAgg = e.target.value as 'sum' | 'avg' | 'count' | 'min' | 'max'
                  setAggregation(newAgg)
                  if (newAgg !== 'count') {
                    // if switching to a math op and current col is string, clear it
                    const curColObj = cols.find(c => c.name === xCol)
                    if (curColObj && curColObj.dtype !== 'numeric') {
                      setXCol('')
                    }
                  }
                }}>
                  <option value="sum">Somme</option>
                  <option value="avg">Moyenne</option>
                  <option value="count">Nombre (Count)</option>
                  <option value="min">Minimum</option>
                  <option value="max">Maximum</option>
                </select>
              </div>

              <div className="db-field" style={{ marginTop: 'var(--space-4)' }}>
                <label htmlFor="kpi-label-input" className="db-label">Libellé</label>
                <input
                  id="kpi-label-input"
                  className="db-input"
                  type="text"
                  placeholder="Ex: Chiffre d'affaires"
                  value={title}
                  onChange={(e) => setTitle(e.target.value)}
                  maxLength={60}
                />
              </div>

              <div className="db-field" style={{ marginTop: 'var(--space-4)' }}>
                <label htmlFor="kpi-format-select" className="db-label">Format de la valeur</label>
                <select id="kpi-format-select" className="db-select" value={format} onChange={(e) => setFormat(e.target.value as any)}>
                  <option value="number">Nombre standard</option>
                  <option value="currency">Devise (€)</option>
                  <option value="percent">Pourcentage (%)</option>
                </select>
              </div>
            </div>

            <hr className="divider" style={{ margin: 'var(--space-5) 0' }} />

            <div className="db-section" style={{ display: 'flex', gap: 'var(--space-2)' }}>
              <button className="btn btn--primary" style={{ flex: 1 }} disabled={!canRender}
                onClick={() => {
                  onSave({ column: xCol, aggregation, label: title, format })
                }}>
                {editingChartId ? 'Mettre a jour' : 'Enregistrer'}
              </button>
              <button className="btn btn--secondary" style={{ flex: 1 }} onClick={onCancel}>
                Annuler
              </button>
            </div>
          </>
        ) : (
          <>
            {isAiGenerated && (
              <div className="ai-banner">
                <Sparkles size={16} strokeWidth={2} className="ai-banner__icon" />
                <div className="ai-banner__content">
                  <p className="ai-banner__title">Graphique généré par Aski</p>
                  <p className="ai-banner__desc">
                    Les colonnes (axes) sont verrouillées pour préserver la structure de ce graphique. Vous pouvez modifier son titre, son type ou ses couleurs.
                  </p>
                </div>
              </div>
            )}

            {/* Chart type */}
            <div className="db-section">
              <p className="db-section-title">Type de graphique</p>
              <div className="chart-type-grid" style={{ display: 'flex', flexWrap: 'wrap', gap: 8 }}>
                {allowedChartTypes.map((ct) => (
                  <ChartTypeBtn
                    key={ct.value}
                    ct={ct}
                    active={chartType === ct.value}
                    onClick={() => setChartType(ct.value)}
                  />
                ))}
              </div>
            </div>

            <hr className="divider" style={{ margin: 'var(--space-5) 0' }} />

            {/* Axes (Hidden for AI graphs) */}
            {!isAiGenerated && (
              <>
                <div className="db-section">
                  <p className="db-section-title">Colonnes</p>

                  {chartType === 'scatter' ? (
                    <>
                      <ColSelect id="x-col-select" label="Axe X (num.)" value={xCol} onChange={setXCol} columns={cols} filter={(c) => c.dtype === 'numeric'} />
                      <ColSelect id="y-col-select" label="Axe Y (num.)" value={yCol} onChange={setYCol} columns={cols} filter={(c) => c.dtype === 'numeric'} />
                    </>
                  ) : chartType === 'pie' ? (
                    <>
                      <ColSelect id="x-col-select" label="Categories" value={xCol} onChange={setXCol} columns={anyCols} />
                      <ColSelect id="y-col-select" label="Valeurs" value={yCol} onChange={setYCol} columns={numCols.length ? numCols : anyCols} filter={(c) => c.dtype === 'numeric'} />
                    </>
                  ) : chartType === 'histogram' ? (
                    <ColSelect id="x-col-select" label="Colonne numerique" value={xCol} onChange={setXCol} columns={cols} filter={(c) => c.dtype === 'numeric'} />
                  ) : (
                    <>
                      <ColSelect id="x-col-select" label="Axe X" value={xCol} onChange={setXCol} columns={anyCols} />
                      <ColSelect id="y-col-select" label="Axe Y" value={yCol} onChange={setYCol} columns={numCols.length ? numCols : anyCols} filter={(c) => c.dtype === 'numeric'} />
                    </>
                  )}
                </div>
                <hr className="divider" style={{ margin: 'var(--space-5) 0' }} />

                {/* Filtres (Smart Filter) */}
                <div className="db-section">
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 8 }}>
                    <p className="db-section-title" style={{ margin: 0 }}>Filtres (Smart Filter)</p>
                    {filters.length < 5 ? (
                      <button
                        className="btn btn--sm btn--ghost"
                        onClick={() => setFilters([...filters, { column: cols[0]?.name || '', operator: '=', value: '' }])}
                        style={{ padding: '4px 8px' }}
                      >
                        <Plus size={14} /> Ajouter
                      </button>
                    ) : (
                      <span style={{ fontSize: 11, color: 'var(--text-3)', fontStyle: 'italic' }}>Limite atteinte (5)</span>
                    )}
                  </div>

                  {filters.length === 0 ? (
                    <p style={{ fontSize: 13, color: 'var(--text-3)', fontStyle: 'italic', margin: 0 }}>Aucun filtre actif.</p>
                  ) : (
                    <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
                      {filters.map((f, i) => (
                        <div key={i} style={{ display: 'flex', gap: 4, alignItems: 'center', background: 'var(--bg-card)', padding: 6, borderRadius: 6, border: '1px solid var(--border-color)' }}>
                          <select
                            value={f.column}
                            onChange={e => { const newF = [...filters]; newF[i].column = e.target.value; setFilters(newF) }}
                            style={{ flex: 1, width: 0, padding: 4, fontSize: 12, borderRadius: 4, border: '1px solid var(--border-color)', background: 'var(--bg-main)', color: 'var(--text-main)' }}
                          >
                            {cols.map(c => <option key={c.name} value={c.name} title={c.name}>{c.name}</option>)}
                          </select>
                          <select
                            value={f.operator}
                            onChange={e => { const newF = [...filters]; newF[i].operator = e.target.value as any; setFilters(newF) }}
                            style={{ width: 70, padding: 4, fontSize: 12, borderRadius: 4, border: '1px solid var(--border-color)', background: 'var(--bg-main)', color: 'var(--text-main)' }}
                          >
                            <option value="=">=</option>
                            <option value="contains">Inclus</option>
                            <option value=">">&gt;</option>
                            <option value="<">&lt;</option>
                          </select>
                          <input
                            type="text"
                            value={f.value}
                            onChange={e => { const newF = [...filters]; newF[i].value = e.target.value; setFilters(newF) }}
                            placeholder="Valeur..."
                            style={{ flex: 1, width: 0, padding: 4, fontSize: 12, borderRadius: 4, border: '1px solid var(--border-color)', background: 'var(--bg-main)', color: 'var(--text-main)' }}
                          />
                          <button
                            onClick={() => setFilters(filters.filter((_, idx) => idx !== i))}
                            style={{ background: 'transparent', border: 'none', color: 'var(--danger)', cursor: 'pointer', padding: 4, display: 'flex', alignItems: 'center' }}
                          >
                            <Trash2 size={14} />
                          </button>
                        </div>
                      ))}
                    </div>
                  )}
                </div>
                <hr className="divider" style={{ margin: 'var(--space-5) 0' }} />
              </>
            )}

            {/* Aggregation (only for grouped charts) */}
            {!isAiGenerated && !['scatter', 'histogram'].includes(chartType) && (
              <>
                <div className="db-section">
                  <p className="db-section-title">Agrégation</p>
                  <div className="db-field">
                    <label htmlFor="agg-select" className="db-label">Fonction d'agrégation</label>
                    <select
                      id="agg-select"
                      className="db-select"
                      value={aggregation}
                      onChange={(e) => setAggregation(e.target.value as any)}
                    >
                      <option value="sum">Somme (Sum)</option>
                      <option value="avg">Moyenne (Average)</option>
                      <option value="count">Nombre (Count)</option>
                      <option value="min">Minimum</option>
                      <option value="max">Maximum</option>
                    </select>
                  </div>
                </div>
                <hr className="divider" style={{ margin: 'var(--space-5) 0' }} />
              </>
            )}
            <div className="db-section">
              <p className="db-section-title">Personnalisation</p>
              <div className="db-field">
                <label htmlFor="chart-title-input" className="db-label">Titre</label>
                <input
                  id="chart-title-input"
                  className="db-input"
                  type="text"
                  placeholder="Titre optionnel..."
                  value={title}
                  onChange={(e) => setTitle(e.target.value)}
                  maxLength={120}
                />
              </div>

              <div className="db-field" style={{ marginTop: 'var(--space-3)' }}>
                <label className="db-label">Palette de couleurs</label>
                <div style={{ display: 'flex', gap: 6, flexWrap: 'wrap', marginTop: 4 }}>
                  {isAiGenerated && (
                    <button
                      title="Couleurs d'origine de l'IA"
                      onClick={() => setPaletteIdx(-1)}
                      style={{
                        display: 'flex', gap: 2, padding: '3px 8px', borderRadius: 6, cursor: 'pointer',
                        background: 'transparent',
                        border: `2px solid ${-1 === paletteIdx ? 'var(--primary)' : 'var(--border-color)'}`,
                        alignItems: 'center', justifyContent: 'center'
                      }}
                    >
                      <span style={{ fontSize: 12, fontWeight: 500, color: 'var(--text-secondary)' }}>Original</span>
                    </button>
                  )}
                  {PALETTES.map((p, i) => (
                    <button
                      key={p.label}
                      title={p.label}
                      onClick={() => setPaletteIdx(i)}
                      style={{
                        display: 'flex', gap: 2, padding: 3, borderRadius: 6, cursor: 'pointer',
                        background: 'transparent',
                        border: `2px solid ${i === paletteIdx ? 'var(--primary)' : 'transparent'}`,
                      }}
                    >
                      {p.colors.slice(0, 4).map(c => (
                        <span key={c} style={{ width: 10, height: 18, borderRadius: 2, background: c, display: 'block' }} />
                      ))}
                    </button>
                  ))}
                </div>
              </div>

              {(chartType === 'line' || chartType === 'area') && (
                <div className="db-field" style={{ marginTop: 'var(--space-4)' }}>
                  <label className="db-label" style={{ display: 'flex', alignItems: 'center', gap: '8px', cursor: 'pointer' }}>
                    <input
                      type="checkbox"
                      checked={smooth}
                      onChange={(e) => setSmooth(e.target.checked)}
                      style={{ width: 16, height: 16, cursor: 'pointer', accentColor: 'var(--primary)' }}
                    />
                    Lisser la courbe
                  </label>
                </div>
              )}
            </div>

            <hr className="divider" style={{ margin: 'var(--space-5) 0' }} />

            {/* Save / Cancel */}
            <div className="db-section" style={{ display: 'flex', gap: 'var(--space-2)' }}>
              <button className="btn btn--primary" style={{ flex: 1 }} disabled={!canRender}
                onClick={() => {
                  if (isAiGenerated) {
                    onSave({ chart_type: chartType, chart_spec: option })
                  } else {
                    onSave({ chart_type: chartType, chart_spec: { ...(option || {}), _meta: { xCol, yCol, title, paletteIdx, smooth, aggregation, filters } } })
                  }
                }}>
                {editingChartId ? 'Mettre a jour' : 'Enregistrer'}
              </button>
              <button className="btn btn--secondary" style={{ flex: 1 }} onClick={onCancel}>
                Annuler
              </button>
            </div>

            <hr className="divider" style={{ margin: 'var(--space-5) 0' }} />

            {/* Export */}
            <div className="db-section">
              <p className="db-section-title">Exporter</p>
              <div className="db-export-row">
                <button
                  id="export-png-btn"
                  className="btn btn--png btn--sm"
                  disabled={!canRender}
                  onClick={handleExportPNG}
                  title="Télécharger en PNG haute résolution"
                >
                  ↓ PNG
                </button>
                <button
                  id="export-csv-btn"
                  className="btn btn--csv btn--sm"
                  disabled={!canRender}
                  onClick={handleExportCSV}
                  title="Exporter les colonnes sélectionnées en CSV"
                >
                  ↓ CSV
                </button>
                <button
                  id="export-excel-btn"
                  className="btn btn--excel btn--sm"
                  disabled={!canRender}
                  onClick={handleExportExcel}
                  title="Formaté pour une lecture directe dans Excel"
                >
                  ↓ Excel
                </button>
                <button
                  id="export-powerbi-btn"
                  className="btn btn--powerbi btn--sm"
                  disabled={!canRender}
                  onClick={handleExportPowerBI}
                  title="Données tabulaires (.xlsx) pour Power Query — ouvrez dans Power BI Desktop pour créer votre visuel"
                >
                  ↓ Power BI
                </button>
              </div>
            </div>
          </>
        )}
      </aside>

      {/* ── Chart area ── */}
      <div className="dashboard-chart-area">
        {builderType === 'kpi' ? (
          canRender && kpiPreviewValue !== null ? (
            <div style={{ display: 'flex', justifyContent: 'center', alignItems: 'center', height: '100%', width: '100%' }}>
              <div className="card" style={{ width: 480, height: 240, padding: 32, display: 'flex', flexDirection: 'column', position: 'relative', border: '1px solid var(--border)', borderRadius: 'var(--radius-xl)', background: 'linear-gradient(145deg, var(--bg-secondary) 0%, var(--surface) 100%)', boxShadow: '0 4px 16px rgba(0,0,0,0.04)', overflow: 'hidden' }}>

                {/* Decorative Icon Background */}
                <div style={{ position: 'absolute', right: -20, bottom: -30, opacity: 0.03, transform: 'rotate(-10deg)', pointerEvents: 'none' }}>
                  {format === 'currency' ? <Euro size={240} strokeWidth={2} /> : format === 'percent' ? <Percent size={240} strokeWidth={2} /> : <Hash size={240} strokeWidth={2} />}
                </div>

                <div style={{ flex: 1, display: 'flex', flexDirection: 'column', justifyContent: 'center', alignItems: 'center', zIndex: 1 }}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: 12, marginBottom: 16 }}>
                    <div style={{ width: 40, height: 40, borderRadius: 10, backgroundColor: 'var(--blue-light)', display: 'flex', alignItems: 'center', justifyContent: 'center', color: 'var(--blue)' }}>
                      {format === 'currency' ? <Euro size={20} strokeWidth={2.5} /> : format === 'percent' ? <Percent size={20} strokeWidth={2.5} /> : <Hash size={20} strokeWidth={2.5} />}
                    </div>
                    <div style={{ fontSize: '1.125rem', color: 'var(--text-secondary)', fontWeight: 600, textTransform: 'uppercase', letterSpacing: '0.05em' }}>
                      {title || 'Votre indicateur clé'}
                    </div>
                  </div>
                  <div style={{ fontSize: '4.5rem', lineHeight: '1', fontWeight: 700, color: 'var(--text-primary)', textShadow: '0 1px 2px rgba(0,0,0,0.05)' }}>
                    {format === 'currency'
                      ? new Intl.NumberFormat('fr-FR', { style: 'currency', currency: 'EUR', maximumFractionDigits: 0 }).format(Number(kpiPreviewValue))
                      : format === 'percent'
                        ? new Intl.NumberFormat('fr-FR', { style: 'percent', maximumFractionDigits: 2 }).format(Number(kpiPreviewValue) / 100)
                        : new Intl.NumberFormat('fr-FR', { maximumFractionDigits: 2 }).format(Number(kpiPreviewValue))
                    }
                  </div>
                </div>
              </div>
            </div>
          ) : (
            <div className="card dashboard-empty-chart">
              <div className="dashboard-empty-chart__inner">
                <div className="section-icon" style={{ width: 48, height: 48, borderRadius: 14 }}>
                  <Hash size={22} strokeWidth={1.75} />
                </div>
                <p className="dashboard-empty-chart__text">
                  Sélectionnez une colonne numérique et une opération pour générer votre KPI.
                </p>
              </div>
            </div>
          )
        ) : canRender && option ? (
          <div className="card dashboard-chart-card dashboard-chart-card--animate">
            <ReactECharts
              key={chartType}
              ref={chartRef}
              option={option}
              style={{ height: 420, width: '100%' }}
              opts={{ renderer: 'canvas' }}
              notMerge
            />
          </div>
        ) : (
          <div className="card dashboard-empty-chart">
            {/* Ghost chart background */}
            <div className="dashboard-empty-chart__bg" aria-hidden="true">
              <svg width="100%" height="100%" viewBox="0 0 400 200" preserveAspectRatio="none">
                <path d="M50 180 L100 120 L150 150 L200 80 L250 110 L300 40 L350 90" stroke="currentColor" strokeWidth="3" fill="none" vectorEffect="non-scaling-stroke" />
                <path d="M50 180 L100 120 L150 150 L200 80 L250 110 L300 40 L350 90 L350 200 L50 200 Z" fill="currentColor" opacity="0.1" />
                <line x1="40" y1="20" x2="40" y2="180" stroke="currentColor" strokeWidth="2" strokeOpacity="0.2" vectorEffect="non-scaling-stroke" />
                <line x1="40" y1="180" x2="380" y2="180" stroke="currentColor" strokeWidth="2" strokeOpacity="0.2" vectorEffect="non-scaling-stroke" />
              </svg>
            </div>

            <div className="dashboard-empty-chart__inner">
              <div className="section-icon" style={{ width: 48, height: 48, borderRadius: 14 }}>
                <IconBarChart size={22} strokeWidth={1.75} />
              </div>
              <p className="dashboard-empty-chart__text">
                Sélectionnez un type de graphique et les colonnes pour visualiser vos données.
              </p>
            </div>
          </div>
        )}

        {/* Dataset info strip */}
        <div className="dashboard-strip">
          <IconFile size={12} strokeWidth={2} />
          <span>{ds.name}</span>
          <span className="footer-dot" />
          <span>{new Intl.NumberFormat('fr-FR').format(ds.rowCount)} lignes</span>
          <span className="footer-dot" />
          <span>{ds.columns.length} colonnes</span>
          {ds.fullData === undefined && (
            <>
              <span className="footer-dot" />
              <span style={{ color: 'var(--warning)' }}>
                Chargement des donnees... (Apercu {rows.length} lignes)
              </span>
            </>
          )}
        </div>
      </div>
    </div>
  )
}

// -- Page wrapper
export function DashboardPage() {
  const activeDs = useDatasetStore((s) => s.getActive())
  const fetchFullData = useDatasetStore((s) => s.fetchFullData)
  const { addChartToDashboard, addKPIToDashboard, updateChartInDashboard, dashboardCharts, loadDashboardConfig, fileId } = useStore()
  const [mode, setMode] = useState<'view' | 'add_chart' | 'add_kpi' | 'edit_chart' | 'edit_kpi'>('view')
  const [editingChartId, setEditingChartId] = useState<string | null>(null)

  useEffect(() => {
    if (fileId) {
      loadDashboardConfig()
    }
  }, [fileId, loadDashboardConfig])

  useEffect(() => {
    if (activeDs?.id) {
      fetchFullData(activeDs.id)
    }
  }, [activeDs?.id, fetchFullData])

  if (!activeDs) {
    return (
      <div className="aski-empty animate-fade-up">
        <div className="aski-empty__inner">
          <p className="aski-empty__text">
            Aucun fichier selectionne. Importez un fichier depuis la page d'accueil.
          </p>
        </div>
      </div>
    )
  }

  // When editing, recover the existing chart's config from _meta (if builder saved it)
  const editingChart = editingChartId ? dashboardCharts.find(c => c.id === editingChartId) : null
  const initialConfig = editingChart ? {
    chartType: (editingChart as any).chart_type as ChartType,
    title: (editingChart as any).chart_spec?._meta?.title || (editingChart as any).chart_spec?.title?.text || (editingChart as any).label || '',
    isAiGenerated: (editingChart as any).chart_type && !(editingChart as any).chart_spec?._meta,
    rawSpec: (editingChart as any).chart_spec,
    ...((editingChart as any).chart_spec?._meta || {}),
    xCol: (editingChart as any).column || (editingChart as any).chart_spec?._meta?.xCol || '',
    aggregation: (editingChart as any).aggregation || (editingChart as any).chart_spec?._meta?.aggregation || 'sum',
  } : undefined

  if (mode === 'add_chart' || mode === 'edit_chart' || mode === 'add_kpi' || mode === 'edit_kpi') {
    const isKpi = mode === 'add_kpi' || mode === 'edit_kpi'
    return (
      <div className="page-transition" key="builder" style={{ flex: 1, display: 'flex', flexDirection: 'column' }}>
        {activeDs.fullDataTruncated && (
          <div style={{ background: 'var(--warning-light, #fef3c7)', color: 'var(--warning-dark, #b45309)', padding: '12px 16px', borderRadius: 8, margin: '16px 24px 0 24px', fontSize: 13, border: '1px solid var(--warning, #f59e0b)', display: 'flex', alignItems: 'center', gap: 12 }}>
            <AlertTriangle size={18} />
            <div>
              <strong>Attention :</strong> Fichier très volumineux. Pour préserver les performances du navigateur, le constructeur manuel analyse un échantillon des 10 000 premières lignes. Pour analyser l'intégralité du fichier, utilisez la vue <strong>Aski</strong>.
            </div>
          </div>
        )}
        <Builder
          ds={activeDs}
          initialConfig={initialConfig}
          editingChartId={editingChartId}
          builderType={isKpi ? 'kpi' : 'chart'}
          onSave={(payload) => {
            if (isKpi) {
              if (editingChartId) {
                updateChartInDashboard(editingChartId, payload)
              } else {
                addKPIToDashboard(payload)
              }
            } else {
              if (editingChartId) {
                updateChartInDashboard(editingChartId, {
                  chart_type: payload.chart_type,
                  chart_spec: payload.chart_spec,
                })
              } else {
                addChartToDashboard(payload)
              }
            }
            setEditingChartId(null)
            setMode('view')
          }}
          onCancel={() => { setEditingChartId(null); setMode('view') }}
        />
      </div>
    )
  }

  return (
    <div className="page-transition" key="view" style={{ flex: 1, display: 'flex', flexDirection: 'column' }}>
      {activeDs.fullDataTruncated && (
        <div style={{ background: 'var(--warning-light, #fef3c7)', color: 'var(--warning-dark, #b45309)', padding: '12px 16px', borderRadius: 8, margin: '16px 24px 0 24px', fontSize: 13, border: '1px solid var(--warning, #f59e0b)', display: 'flex', alignItems: 'center', gap: 12 }}>
          <AlertTriangle size={18} />
          <div>
            <strong>Attention :</strong> Fichier très volumineux. Pour préserver les performances du navigateur, le constructeur manuel analyse un échantillon des 10 000 premières lignes. Pour analyser l'intégralité du fichier, utilisez la vue <strong>Aski</strong>.
          </div>
        </div>
      )}
      <DashboardView
        onAddChart={() => { setEditingChartId(null); setMode('add_chart') }}
        onEditChart={(id) => { setEditingChartId(id); setMode('edit_chart') }}
        onAddKPI={() => { setEditingChartId(null); setMode('add_kpi') }}
        onEditKPI={(id) => { setEditingChartId(id); setMode('edit_kpi') }}
      />
    </div>
  )
}
