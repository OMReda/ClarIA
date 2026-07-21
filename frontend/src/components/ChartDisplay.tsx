import React from 'react'
import ReactECharts from 'echarts-for-react'
import { useStore } from '../store'
import { BarChart, LineChart, PieChart, Activity, Grip, BarChart2, Target, Grid } from 'lucide-react'
import { exportCSV, exportExcel, exportPowerBI, exportPNG, extractDataFromSpec } from '../utils/exportUtils'

const CHART_TYPE_LABELS: Record<string, string> = {
  bar: 'Graphique en barres', line: 'Courbe temporelle', pie: 'Camembert',
  scatter: 'Nuage de points', histogram: 'Histogramme', radar: 'Radar', heatmap: 'Heatmap'
}

function ChartIcon({ type }: { type: string }) {
  switch (type) {
    case 'bar': return <BarChart size={16} />
    case 'line': return <LineChart size={16} />
    case 'pie': return <PieChart size={16} />
    case 'scatter': return <Activity size={16} />
    case 'histogram': return <BarChart2 size={16} />
    case 'radar': return <Target size={16} />
    case 'heatmap': return <Grid size={16} />
    default: return <Grip size={16} />
  }
}

// Light-mode ECharts theme overrides
function lightSpec(spec: Record<string, unknown>): Record<string, unknown> {
  const s = { ...spec }
  const axisStyle = {
    axisLabel: { color: '#475569', fontSize: 12, fontFamily: 'Inter, sans-serif' },
    axisLine: { lineStyle: { color: '#e2e8f0' } },
    splitLine: { lineStyle: { color: '#f1f5f9' } },
    axisTick: { lineStyle: { color: '#e2e8f0' } },
    nameTextStyle: { color: '#94a3b8' },
  }
  if (s.xAxis) s.xAxis = { ...(s.xAxis as object), ...axisStyle }
  if (s.yAxis) s.yAxis = { ...(s.yAxis as object), ...axisStyle }
  // Always hide the in-canvas title — the UI renders its own header
  const titleObj = s.title as Record<string, unknown> | undefined
  s.title = { ...(titleObj || {}), show: false }
  return {
    backgroundColor: 'transparent',
    textStyle: { color: '#0f172a', fontFamily: 'Inter, sans-serif' },
    tooltip: {
      backgroundColor: '#ffffff',
      borderColor: '#e2e8f0',
      borderWidth: 1,
      textStyle: { color: '#0f172a', fontSize: 13 },
      extraCssText: 'box-shadow: 0 4px 12px rgba(15,23,42,0.10); border-radius: 10px;',
    },
    color: ['#2563eb', '#7c3aed', '#0891b2', '#059669', '#d97706', '#dc2626'],
    legend: { textStyle: { color: '#475569', fontSize: 12 } },
    ...s,
  }
}

export function ChartDisplay() {
  const { chart, status, explanation, fileName } = useStore()
  const chartRef = React.useRef<ReactECharts>(null)
  const [elapsed, setElapsed] = React.useState(0)

  // Elapsed timer while processing — gives user feedback when Ollama is loading
  React.useEffect(() => {
    if (status !== 'processing') { setElapsed(0); return }
    const t = setInterval(() => setElapsed(s => s + 1), 1000)
    return () => clearInterval(t)
  }, [status])

  const handleExportPNG = () => {
    exportPNG(chartRef, `${fileName || 'export'}-chart.png`)
  }

  const handleExportCSV = () => {
    if (!chart?.chart_spec) return
    const { rows, cols } = extractDataFromSpec(chart.chart_spec)
    exportCSV(rows, cols, `${fileName || 'export'}-export.csv`)
  }

  const handleExportExcel = () => {
    if (!chart?.chart_spec) return
    const { rows, cols } = extractDataFromSpec(chart.chart_spec)
    exportExcel(rows, cols, `${fileName || 'export'}-excel.xlsx`)
  }

  const handleExportPowerBI = () => {
    if (!chart?.chart_spec) return
    const { rows, cols } = extractDataFromSpec(chart.chart_spec)
    exportPowerBI(rows, cols, `${fileName || 'export'}-powerbi.xlsx`)
  }

  if (status === 'processing') {
    return (
      <div id="chart-display" aria-live="polite">
        <div className="section-header">
          <div className="section-icon">
            <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
              <line x1="18" y1="20" x2="18" y2="10" /><line x1="12" y1="20" x2="12" y2="4" />
              <line x1="6" y1="20" x2="6" y2="14" />
            </svg>
          </div>
          <div>
            <p className="section-header__title">Generation du graphique...</p>
            <p className="section-header__sub">L'IA analyse votre fichier</p>
          </div>
        </div>
        <div className="chart-placeholder">
          <div className="chart-placeholder__inner">
            <div className="spinner spinner--lg" />
            <p>Traitement en cours{elapsed > 0 ? ` (${elapsed}s)` : ''}...</p>
            {elapsed >= 8 && (
              <p style={{ fontSize: 12, color: 'var(--text-tertiary)', marginTop: 4 }}>
                Ollama charge le modele, cela peut prendre jusqu'a 30-60s au premier appel.
              </p>
            )}
          </div>
        </div>
      </div>
    )
  }

  if (!chart) return null

  return (
    <div className="chart-display" id="chart-display" aria-label="Graphique généré">
      <div className="section-header" style={{ marginBottom: 'var(--space-5)' }}>
        <div className="section-icon">
          <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
            <line x1="18" y1="20" x2="18" y2="10" /><line x1="12" y1="20" x2="12" y2="4" />
            <line x1="6" y1="20" x2="6" y2="14" />
          </svg>
        </div>
        <div style={{ flex: 1 }}>
          <p className="section-header__title">Résultat</p>
          <p className="section-header__sub">Graphique généré par l'IA</p>
        </div>
        <span className="badge badge--blue" style={{ display: 'inline-flex', alignItems: 'center', gap: '4px' }}>
          <ChartIcon type={chart.chart_type} /> {CHART_TYPE_LABELS[chart.chart_type] ?? chart.chart_type}
        </span>
      </div>

      <div className="chart-display__inner">
        <ReactECharts
          ref={chartRef}
          option={lightSpec(chart.chart_spec as Record<string, unknown>)}
          style={{ height: '400px', width: '100%' }}
          opts={{ renderer: 'svg' }}
          notMerge
        />

        {explanation && (
          <div className="explanation-card animate-fade-in" aria-label="Explication du graphique">
            <span className="explanation-card__icon" aria-hidden="true">💡</span>
            <p className="explanation-card__text">{explanation}</p>
          </div>
        )}

        <div className="db-export-row" style={{ marginTop: 'var(--space-4)', justifyContent: 'flex-end', flexWrap: 'wrap' }}>
          <button className="btn btn--primary btn--sm" onClick={() => useStore.getState().addChartToDashboard(chart)} title="Ajouter ce graphique au tableau de bord">
            + Tableau de bord
          </button>
          <div style={{ flex: 1 }} />
          <button className="btn btn--png btn--sm" onClick={handleExportPNG} title="Télécharger en PNG haute résolution">↓ PNG</button>
          <button className="btn btn--csv btn--sm" onClick={handleExportCSV} title="Exporter les données en CSV">↓ CSV</button>
          <button className="btn btn--excel btn--sm" onClick={handleExportExcel} title="Formaté pour une lecture directe dans Excel">↓ Excel</button>
          <button className="btn btn--powerbi btn--sm" onClick={handleExportPowerBI} title="Données brutes optimisées pour Power Query">↓ Power BI</button>
        </div>
      </div>
    </div>
  )
}
