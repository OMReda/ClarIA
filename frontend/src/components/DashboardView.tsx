import React, { useEffect, useMemo } from 'react'
import { ResponsiveGridLayout, useContainerWidth } from 'react-grid-layout'
import ReactECharts from 'echarts-for-react'
import { useStore } from '../store'
import { ChartPayload } from '../api/types'
import { IconSettings, IconBarChart, IconX } from './Icon'
import { LayoutDashboard, Trash2, AlertCircle, RefreshCcw, BarChart3, BarChart2, LayoutGrid, Download, Plus, Hash, Wand2 } from 'lucide-react'
import { createPortal } from 'react-dom'
import { KPICard } from './KPICard'
import { DashboardGraph, DashboardKPI } from '../store'
import { DndContext, closestCenter, KeyboardSensor, PointerSensor, useSensor, useSensors, DragEndEvent } from '@dnd-kit/core'
import { arrayMove, SortableContext, sortableKeyboardCoordinates, horizontalListSortingStrategy, useSortable } from '@dnd-kit/sortable'
import { CSS } from '@dnd-kit/utilities'
import { restrictToHorizontalAxis } from '@dnd-kit/modifiers'

// Force ECharts to resize perfectly even when its container is animated by react-grid-layout
function ResponsiveChart({ option }: { option: any }) {
  const containerRef = React.useRef<HTMLDivElement>(null)
  const chartRef = React.useRef<any>(null)

  React.useEffect(() => {
    if (!containerRef.current) return
    const ro = new ResizeObserver((entries) => {
      for (const entry of entries) {
        const { width, height } = entry.contentRect
        if (width > 0 && height > 0) {
          try {
            chartRef.current?.getEchartsInstance()?.resize({ width, height })
          } catch (e) { }
        }
      }
    })
    ro.observe(containerRef.current)
    return () => ro.disconnect()
  }, [])

  return (
    <div ref={containerRef} style={{ width: '100%', height: '100%' }}>
      <ReactECharts
        ref={chartRef}
        option={option}
        style={{ height: '100%', width: '100%' }}
        opts={{ renderer: 'canvas' }}
        notMerge
      />
    </div>
  )
}

function SortableKPIItem({ kpi, onEditKPI, setChartToDelete, isDeleting }: { kpi: DashboardKPI, onEditKPI: (id: string) => void, setChartToDelete: (id: string) => void, isDeleting?: boolean }) {
  const { attributes, listeners, setNodeRef, transform, transition, isDragging } = useSortable({ id: kpi.id })

  const style = {
    flex: '0 0 auto',
    transform: CSS.Transform.toString(transform),
    transition,
    zIndex: isDragging ? 100 : 1,
    opacity: isDragging ? 0.8 : 1,
    cursor: isDragging ? 'grabbing' : 'grab',
  }

  return (
    <div ref={setNodeRef} style={style} {...attributes} {...listeners} className={isDeleting ? 'animate-fade-out-scale' : ''}>
      <KPICard
        id={kpi.id}
        column={kpi.column}
        aggregation={kpi.aggregation}
        label={kpi.label}
        format={kpi.format}
        filters={kpi.filters ?? []}
        onEdit={onEditKPI}
        onDelete={setChartToDelete}
      />
    </div>
  )
}


export function DashboardView({ onAddChart, onEditChart, onAddKPI, onEditKPI }: { onAddChart: () => void, onEditChart: (id: string) => void, onAddKPI: () => void, onEditKPI: (id: string) => void }) {
  const { dashboardCharts, saveDashboardLayout, removeChartFromDashboard, loadDashboardConfig, fileId, reorderKPIs, isDashboardLoading } = useStore()
  const { width, containerRef, mounted } = useContainerWidth()
  const [chartToDelete, setChartToDelete] = React.useState<string | null>(null)
  const [chartActuallyDeleting, setChartActuallyDeleting] = React.useState<string | null>(null)

  const kpis = useMemo(() => dashboardCharts.filter(c => (c.type ?? 'chart') === 'kpi') as DashboardKPI[], [dashboardCharts])
  const graphs = useMemo(() => dashboardCharts.filter(c => (c.type ?? 'chart') === 'chart') as DashboardGraph[], [dashboardCharts])

  const sensors = useSensors(
    useSensor(PointerSensor, {
      activationConstraint: {
        distance: 5,
      },
    }),
    useSensor(KeyboardSensor, {
      coordinateGetter: sortableKeyboardCoordinates,
    })
  )

  const handleDragStart = () => {
    // Intentionally empty: removed auto-animate conflict
  }

  const handleDragEnd = (event: DragEndEvent) => {
    const { active, over } = event
    if (active.id !== over?.id) {
      const oldIndex = kpis.findIndex((kpi) => kpi.id === active.id)
      const newIndex = kpis.findIndex((kpi) => kpi.id === over?.id)
      if (oldIndex !== -1 && newIndex !== -1) {
        reorderKPIs(oldIndex, newIndex)
      }
    }
  }

  const layout = useMemo(() => {
    return graphs.map(c => ({
      i: c.id,
      x: c.layout.x,
      y: c.layout.y,
      w: c.layout.w,
      h: c.layout.h
    }))
  }, [graphs])

  const onDragStop = (layout: any) => {
    saveDashboardLayout(layout.map((l: any) => ({ id: l.i, x: l.x, y: l.y, w: l.w, h: l.h })))
  }

  const onResizeStop = (layout: any) => {
    saveDashboardLayout(layout.map((l: any) => ({ id: l.i, x: l.x, y: l.y, w: l.w, h: l.h })))
  }

  if (!fileId) {
    return (
      <div className="db-empty animate-fade-up">
        <div className="db-empty__card">
          <div className="db-empty__icon-wrapper">
            <LayoutDashboard size={40} strokeWidth={1.5} color="var(--blue)" />
          </div>
          <h2 className="db-empty__title">Bienvenue dans votre espace d'analyse</h2>
          <p className="db-empty__subtitle">
            Il semble que vous n'ayez pas encore importé de données. Veuillez charger un fichier pour commencer à générer votre tableau de bord.
          </p>
          <div className="db-empty__features">
            {[
              { icon: <Wand2 size={24} strokeWidth={1.5} color="var(--blue)" />, label: 'Génération IA', desc: 'Créez des graphiques instantanément avec Aski' },
              { icon: <BarChart2 size={24} strokeWidth={1.5} color="var(--blue)" />, label: 'Visualisation', desc: 'Explorez vos données via des tableaux et graphiques' },
              { icon: <Download size={24} strokeWidth={1.5} color="var(--blue)" />, label: 'Export multi-formats', desc: 'PNG, CSV, Excel, Power BI' },
            ].map(f => (
              <div key={f.label} className="db-empty__feature-card">
                <div className="db-empty__feature-icon-box">
                  {f.icon}
                </div>
                <div className="db-empty__feature-text">
                  <p className="db-empty__feature-title">{f.label}</p>
                  <p className="db-empty__feature-desc">{f.desc}</p>
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>
    )
  }

  if (isDashboardLoading) {
    return (
      <div className="db-empty animate-fade-up" style={{ alignItems: 'center', justifyContent: 'center' }}>
        <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 20 }}>
          <div className="spinner spinner--lg" />
          <p style={{ color: 'var(--text-tertiary)', fontSize: 14, fontWeight: 500 }}>Chargement du tableau de bord…</p>
        </div>
      </div>
    )
  }

  if (dashboardCharts.length === 0) {
    return (
      <div className="db-empty animate-fade-up">
        {/* Ambient background glows */}
        <div className="db-empty__ambient db-empty__ambient--1" aria-hidden="true" />
        <div className="db-empty__ambient db-empty__ambient--2" aria-hidden="true" />

        <div className="db-empty__content">
          <div className="db-empty__hero">
            <h2 className="db-empty__title">
              Votre tableau de bord
            </h2>
            <p className="db-empty__subtitle">
              Transformez vos données brutes en visualisations claires. Ajoutez des graphiques, réorganisez-les et exportez vos résultats.
            </p>
            <div style={{ display: 'flex', gap: 12, justifyContent: 'center' }}>
              <button className="btn btn--primary db-empty__cta" onClick={onAddChart} style={{ margin: 0 }}>
                <span className="db-empty__cta-icon">+</span> Ajouter un graphique
              </button>
              <button className="btn btn--secondary db-empty__cta db-empty__cta--secondary" onClick={onAddKPI} style={{ margin: 0 }}>
                <Plus size={16} style={{ marginRight: 6 }} /> Ajouter un KPI
              </button>
            </div>
          </div>

          <div className="db-empty__features">
            {[
              { icon: <BarChart3 size={24} strokeWidth={1.5} color="var(--blue)" />, label: '8 types de graphiques', desc: 'Barres, courbes, radar, heatmap et plus' },
              { icon: <Hash size={24} strokeWidth={1.5} color="var(--blue)" />, label: 'Indicateurs clés', desc: 'Suivez vos métriques en temps réel' },
              { icon: <LayoutGrid size={24} strokeWidth={1.5} color="var(--blue)" />, label: 'Drag & Resize', desc: 'Agencement entièrement libre' },
            ].map(f => (
              <div key={f.label} className="db-empty__feature-card">
                <div className="db-empty__feature-icon-box">
                  {f.icon}
                </div>
                <div className="db-empty__feature-text">
                  <p className="db-empty__feature-title">{f.label}</p>
                  <p className="db-empty__feature-desc">{f.desc}</p>
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>
    )
  }

  const isDesktop = width > 768;

  return (
    <div className="dashboard-view-container" ref={containerRef as any} style={{ width: '100%', overflowX: 'hidden', padding: 'var(--space-8) var(--space-10) var(--space-16)' }}>
      {/* KPI Section Header */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 'var(--space-6)' }}>
        <h2 style={{ margin: 0, fontWeight: 600 }}>Tableau de bord</h2>
        <button className="btn btn--soft-blue btn--sm" onClick={onAddKPI}>+ KPI</button>
      </div>

      {/* KPI List */}
      {kpis.length > 0 && (
        <div style={{ paddingBottom: 'var(--space-4)' }}>
          <DndContext sensors={sensors} collisionDetection={closestCenter} onDragStart={handleDragStart} onDragEnd={handleDragEnd} modifiers={[restrictToHorizontalAxis]}>
            <SortableContext items={kpis.map(k => k.id)} strategy={horizontalListSortingStrategy}>
              <div className="dashboard-kpi-list" style={{ display: 'flex', flexWrap: 'nowrap', gap: 'var(--space-4)', overflowX: 'auto', paddingBottom: 16 }}>
                {kpis.map(kpi => (
                  <SortableKPIItem
                    key={kpi.id}
                    kpi={kpi}
                    onEditKPI={onEditKPI}
                    setChartToDelete={setChartToDelete}
                    isDeleting={chartActuallyDeleting === kpi.id}
                  />
                ))}
              </div>
            </SortableContext>
          </DndContext>
        </div>
      )}

      {/* Divider */}
      <hr style={{ border: 0, borderTop: '1px solid var(--border)', margin: 'var(--space-4) 0 var(--space-8) 0' }} />

      {/* Graphs Section Header */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 'var(--space-6)' }}>
        <h3 style={{ margin: 0, fontWeight: 600, fontSize: '1.25rem' }}>Analyses Détaillées</h3>
        <button className="btn btn--primary btn--sm" onClick={onAddChart}>+ Graphique</button>
      </div>

      <div style={{ margin: '0 -12px' }}>
        {mounted && (
          <ResponsiveGridLayout
            layouts={{ lg: layout }}
            breakpoints={{ lg: 1200, md: 996, sm: 768, xs: 480, xxs: 0 }}
            cols={{ lg: 12, md: 10, sm: 6, xs: 4, xxs: 2 }}
            rowHeight={100}
            width={width}
            margin={[24, 24]}
            // @ts-ignore - measureBeforeMount exists at runtime but is missing from typings
            measureBeforeMount={true}
            compactType="vertical"
            isDraggable={isDesktop}
            isResizable={isDesktop}
            draggableHandle=".drag-handle"
            onDragStop={onDragStop}
            onResizeStop={onResizeStop}
          >
            {graphs.map(chart => {
              let option = { ...chart.chart_spec };

              if (option.title) {
                option.title = { ...option.title, show: false };
              } else {
                option.title = { show: false };
              }

              if (chart.chart_type === 'pie' && Array.isArray(option.series)) {
                option.series = option.series.map((s: any) => ({ ...s, center: ['50%', '50%'] }));
              }

              if (['bar', 'line', 'area', 'scatter', 'histogram'].includes(chart.chart_type)) {
                option.grid = { ...option.grid, left: 60, right: 20, bottom: 45, top: 55, containLabel: true };
              }
              
              if (option.yAxis) {
                const yAxes = Array.isArray(option.yAxis) ? option.yAxis : [option.yAxis];
                yAxes.forEach((yAxis: any) => {
                  if (yAxis.name) {
                    yAxis.nameGap = 12;
                  }
                });
              }

              return (
                <div key={chart.id}>
                  <div className={`card dashboard-card ${chartActuallyDeleting === chart.id ? 'animate-fade-out-scale' : ''}`} style={{ display: 'flex', flexDirection: 'column', height: '100%', overflow: 'hidden' }}>
                    <div className="dashboard-card-header drag-handle" style={{ cursor: isDesktop ? 'grab' : 'default', display: 'flex', justifyContent: 'space-between', padding: 'var(--space-3) var(--space-4)', borderBottom: '1px solid var(--border)', backgroundColor: 'var(--bg-secondary)', borderTopLeftRadius: 'var(--radius-lg)', borderTopRightRadius: 'var(--radius-lg)', flexShrink: 0 }}>
                      <div style={{ fontWeight: 600, fontSize: '0.875rem' }}>
                        {chart.chart_spec?._meta?.title || chart.chart_spec?.title?.text || chart.chart_type}
                      </div>
                      <div style={{ display: 'flex', gap: 'var(--space-2)' }}>
                        <button className="btn btn--ghost btn--icon btn--sm" onClick={() => onEditChart(chart.id)} title="Modifier">
                          <IconSettings size={14} />
                        </button>
                        <button className="btn btn--ghost btn--icon btn--sm" onClick={() => setChartToDelete(chart.id)} title="Supprimer">
                          <Trash2 size={14} />
                        </button>
                      </div>
                    </div>
                    <div className="dashboard-card-body" style={{ padding: 'var(--space-2)', flex: 1, minHeight: 0, position: 'relative' }}>
                      <div style={{ position: 'absolute', top: 'var(--space-2)', left: 'var(--space-2)', right: 'var(--space-2)', bottom: 'var(--space-2)' }}>
                        <ResponsiveChart option={option} />
                      </div>
                    </div>
                  </div>
                </div>
              )
            })}
          </ResponsiveGridLayout>
        )}
      </div>

      {chartToDelete && (() => {
        const itemToDelete = dashboardCharts.find(c => c.id === chartToDelete)
        const isKpi = (itemToDelete?.type ?? 'chart') === 'kpi'
        const itemTypeLabel = isKpi ? 'ce KPI' : 'ce graphique'

        return createPortal(
          <div
            className="settings-backdrop"
            onClick={(e) => e.target === e.currentTarget && setChartToDelete(null)}
            role="dialog"
            aria-modal="true"
          >
            <div className="settings-panel animate-scale-in" style={{ maxWidth: 400, width: '100%', padding: 0 }}>
              <div className="settings-panel__header">
                <div style={{ display: 'flex', alignItems: 'center', gap: 'var(--space-3)' }}>
                  <h3 style={{ margin: 0, fontSize: '15px', fontWeight: 600 }}>Confirmer la suppression</h3>
                </div>
                <button className="btn btn--ghost btn--icon" onClick={() => setChartToDelete(null)} style={{ width: 28, height: 28, borderRadius: '50%' }}>
                  <IconX size={14} strokeWidth={2} />
                </button>
              </div>
              <div className="settings-panel__body">
                <p style={{ margin: 0, fontSize: 14, color: 'var(--text-2)', lineHeight: 1.5 }}>
                  Êtes-vous sûr de vouloir supprimer {itemTypeLabel} ? Cette action est irréversible.
                </p>
                <div style={{ display: 'flex', gap: 8, justifyContent: 'flex-end', marginTop: 24 }}>
                  <button className="btn btn--ghost btn--sm" onClick={() => setChartToDelete(null)}>Annuler</button>
                  <button className="btn btn--primary btn--sm" style={{ background: 'var(--danger)', borderColor: 'var(--danger)', color: '#fff' }} onClick={() => {
                    if (isKpi) {
                      removeChartFromDashboard(chartToDelete)
                    } else {
                      setChartActuallyDeleting(chartToDelete)
                      setTimeout(() => {
                        removeChartFromDashboard(chartToDelete)
                        setChartActuallyDeleting(null)
                      }, 300)
                    }
                    setChartToDelete(null)
                  }}>
                    Supprimer
                  </button>
                </div>
              </div>
            </div>
          </div>,
          document.body
        )
      })()}
    </div>
  )
}
