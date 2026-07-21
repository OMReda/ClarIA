import { create } from 'zustand'
import type { ChartPayload, ColumnInfo, FileUploadResponse } from '../api/types'
import { useDatasetStore } from './datasetStore'
import { generateUUID } from '../utils/uuid'

export type AppStatus =
  | 'idle'
  | 'uploading'
  | 'previewing'
  | 'needs_sheet'
  | 'prompting'
  | 'processing'
  | 'awaiting_clarification'
  | 'completed'
  | 'error'

export type ToastSeverity = 'info' | 'success' | 'error' | 'warning'

export interface Toast {
  id: string
  severity: ToastSeverity
  message: string
}

export interface DashboardBase {
  id: string
  type?: 'chart' | 'kpi'
}

export interface DashboardGraph extends DashboardBase {
  type?: 'chart'
  chart_type: string
  chart_spec: Record<string, any>
  layout: { x: number; y: number; w: number; h: number }
}

export interface DashboardKPI extends DashboardBase {
  type: 'kpi'
  column: string
  aggregation: 'sum' | 'avg' | 'count' | 'min' | 'max'
  label: string
  format?: 'number' | 'currency' | 'percent'
}

export type DashboardChart = DashboardGraph | DashboardKPI

export interface AppState {
  isHydrating: boolean
  status: AppStatus
  fileId: string | null
  fileName: string | null
  rowCount: number | null
  columns: ColumnInfo[]
  previewRows: Record<string, unknown>[]
  sheetNames: string[]

  currentPromptId: string | null
  chart: ChartPayload | null
  explanation: string | null
  clarificationQuestion: string | null
  errorMessage: string | null

  dashboardCharts: DashboardChart[]

  toasts: Toast[]

  /** Active WebSocket for the current prompt. Single owner — setActiveWs closes
   *  the previous socket before installing a new one to prevent leaks. */
  activeWs: WebSocket | null

  config: { max_file_size_mb: number; max_rows: number } | null

  lastPromptText: string | null

  // Actions
  fetchConfig: () => Promise<void>
  setUploadResult: (res: FileUploadResponse, fileName: string) => void
  setStatus: (s: AppStatus) => void
  setPromptId: (id: string | null) => void
  setChart: (c: ChartPayload | null, explanation?: string | null) => void
  setClarification: (q: string | null) => void
  setError: (msg: string | null) => void
  setLastPromptText: (text: string | null) => void
  resetPrompt: () => void
  resetAll: () => void
  addToast: (severity: ToastSeverity, message: string) => void
  dismissToast: (id: string) => void
  /** Close any existing WebSocket, then store the new one (or null to just close). */
  setActiveWs: (ws: WebSocket | null) => void
  hydrateSession: () => Promise<void>

  loadDashboardConfig: () => Promise<void>
  addChartToDashboard: (chart: ChartPayload) => void
  addKPIToDashboard: (kpi: Omit<DashboardKPI, 'id' | 'type'>) => void
  updateChartInDashboard: (id: string, updates: Partial<DashboardGraph> | Partial<DashboardKPI>) => void
  removeChartFromDashboard: (id: string) => void
  saveDashboardLayout: (layouts: { id: string; x: number; y: number; w: number; h: number }[]) => void
  reorderKPIs: (oldIndex: number, newIndex: number) => void
}

export const useStore = create<AppState>((set, get) => ({
  isHydrating: true,
  status: 'idle',
  fileId: null,
  fileName: null,
  rowCount: null,
  columns: [],
  previewRows: [],
  sheetNames: [],
  currentPromptId: null,
  chart: null,
  explanation: null,
  clarificationQuestion: null,
  errorMessage: null,
  dashboardCharts: [],
  toasts: [],
  activeWs: null,
  config: null,
  lastPromptText: null,

  loadDashboardConfig: async () => {
    const fileId = get().fileId
    if (!fileId) return
    try {
      const { getDashboardConfig } = await import('../api/client')
      const config = await getDashboardConfig(fileId)
      if (config && Array.isArray(config.charts)) {
        let charts = [...config.charts];

        // Auto-fix old naive vertical stacks once on load so they pack into 2 columns
        const isNaiveStack = charts.length > 0 && charts.every((c: any) => c.layout.w === 6 || c.layout.w === 8);
        if (isNaiveStack) {
          charts = charts.map((c: any, index: number) => ({
            ...c,
            layout: { ...c.layout, w: 6, x: (index % 2) * 6, y: Math.floor(index / 2) * 4 }
          }));
        }

        set({ dashboardCharts: charts })
      } else {
        set({ dashboardCharts: [] })
      }
    } catch {
      // ignore
    }
  },

  addChartToDashboard: async (chart: ChartPayload) => {
    const fileId = get().fileId
    if (!fileId) return
    const id = chart.chart_id || generateUUID()

    const currentCharts = get().dashboardCharts
    
    // Prevent duplicates by comparing chart specifications
    const newSpecStr = JSON.stringify(chart.chart_spec)
    const isDuplicate = currentCharts.some(c => (c.type ?? 'chart') === 'chart' && JSON.stringify((c as DashboardGraph).chart_spec) === newSpecStr)
    if (isDuplicate) {
      get().addToast('error', 'Ce graphique existe déjà sur le tableau de bord.')
      return
    }

    const graphsCount = currentCharts.filter(c => (c.type ?? 'chart') !== 'kpi').length;
    // Find the lowest available spot intuitively
    const w = 6;
    const h = 4;
    const x = (graphsCount % 2) * 6; // alternate between 0 and 6
    const y = Infinity; // RGL will automatically pack it downwards

    const newChart: DashboardChart = {
      id,
      chart_type: chart.chart_type,
      chart_spec: chart.chart_spec,
      layout: { x, y, w, h }
    }
    const updatedCharts = [...currentCharts, newChart]

    // Optimistic update
    set({ dashboardCharts: updatedCharts })

    try {
      const { saveDashboardConfig } = await import('../api/client')
      await saveDashboardConfig(fileId, { charts: updatedCharts })
      get().addToast('success', 'Graphique ajouté au tableau de bord.')
    } catch (e) {
      // Rollback
      set({ dashboardCharts: currentCharts })
      get().addToast('error', 'Erreur lors de la sauvegarde du tableau de bord.')
    }
  },

  addKPIToDashboard: async (kpiConfig) => {
    const fileId = get().fileId
    if (!fileId) return

    const currentCharts = get().dashboardCharts
    
    // Prevent duplicate KPIs
    const isDuplicate = currentCharts.some(c => 
      (c.type ?? 'chart') === 'kpi' && 
      (c as DashboardKPI).column === kpiConfig.column && 
      (c as DashboardKPI).aggregation === kpiConfig.aggregation
    )
    
    if (isDuplicate) {
      get().addToast('error', 'Ce KPI existe déjà sur le tableau de bord.')
      return
    }

    const newKpi: DashboardKPI = {
      id: generateUUID(),
      type: 'kpi',
      ...kpiConfig,
    }
    const updatedCharts = [...currentCharts, newKpi]

    set({ dashboardCharts: updatedCharts })

    try {
      const { saveDashboardConfig } = await import('../api/client')
      await saveDashboardConfig(fileId, { charts: updatedCharts })
      get().addToast('success', 'KPI ajouté au tableau de bord.')
    } catch (e) {
      set({ dashboardCharts: currentCharts })
      get().addToast('error', 'Erreur lors de la sauvegarde du tableau de bord.')
    }
  },

  updateChartInDashboard: async (id: string, updates: Partial<DashboardGraph> | Partial<DashboardKPI>) => {
    const fileId = get().fileId
    if (!fileId) return

    const currentCharts = get().dashboardCharts
    const updatedCharts = currentCharts.map(c => c.id === id ? { ...c, ...updates } as DashboardChart : c)

    set({ dashboardCharts: updatedCharts })

    try {
      const { saveDashboardConfig } = await import('../api/client')
      await saveDashboardConfig(fileId, { charts: updatedCharts })
    } catch (e) {
      set({ dashboardCharts: currentCharts })
      get().addToast('error', 'Erreur lors de la mise à jour.')
    }
  },

  removeChartFromDashboard: async (id: string) => {
    const fileId = get().fileId
    if (!fileId) return

    const currentCharts = get().dashboardCharts
    const chartToRemove = currentCharts.find(c => c.id === id)
    let updatedCharts = currentCharts.filter(c => c.id !== id)

    // Automatically reflow graphs if a graph was deleted to close horizontal gaps
    if (chartToRemove && (chartToRemove.type ?? 'chart') === 'chart') {
      let remainingGraphs = updatedCharts.filter(c => (c.type ?? 'chart') === 'chart') as DashboardGraph[];
      
      // Sort in reading order (top-to-bottom, left-to-right)
      remainingGraphs.sort((a, b) => {
        if (a.layout.y !== b.layout.y) return a.layout.y - b.layout.y;
        return a.layout.x - b.layout.x;
      });

      let currentX = 0;
      let currentY = 0;
      let rowHeight = 0;

      const newGraphs = remainingGraphs.map(g => {
        if (currentX + g.layout.w > 12) {
          currentX = 0;
          currentY += rowHeight || g.layout.h;
          rowHeight = 0;
        }

        const newLayout = { ...g.layout, x: currentX, y: currentY };
        currentX += g.layout.w;
        rowHeight = Math.max(rowHeight, g.layout.h);

        return { ...g, layout: newLayout };
      });

      updatedCharts = updatedCharts.map(c => {
        if ((c.type ?? 'chart') === 'chart') {
          return newGraphs.find(ng => ng.id === c.id) || c;
        }
        return c;
      });
    }

    set({ dashboardCharts: updatedCharts })

    try {
      const { saveDashboardConfig } = await import('../api/client')
      await saveDashboardConfig(fileId, { charts: updatedCharts })
    } catch (e) {
      set({ dashboardCharts: currentCharts })
      get().addToast('error', 'Erreur lors de la suppression.')
    }
  },

  saveDashboardLayout: async (layouts) => {
    const fileId = get().fileId
    if (!fileId) return

    const currentCharts = get().dashboardCharts
    const updatedCharts = currentCharts.map(c => {
      if ((c.type ?? 'chart') === 'kpi') return c;
      const l = layouts.find(lo => lo.id === c.id)
      return l ? { ...c, layout: { x: l.x, y: l.y, w: l.w, h: l.h } } : c
    }) as DashboardChart[]

    set({ dashboardCharts: updatedCharts })

    try {
      const { saveDashboardConfig } = await import('../api/client')
      await saveDashboardConfig(fileId, { charts: updatedCharts })
    } catch (e) {
      set({ dashboardCharts: currentCharts })
      get().addToast('error', 'Erreur lors de la sauvegarde de la disposition.')
    }
  },

  reorderKPIs: async (oldIndex, newIndex) => {
    const fileId = get().fileId
    if (!fileId) return
    const current = get().dashboardCharts
    const kpis = current.filter(c => (c.type ?? 'chart') === 'kpi')
    const graphs = current.filter(c => (c.type ?? 'chart') !== 'kpi')
    
    const item = kpis.splice(oldIndex, 1)[0]
    kpis.splice(newIndex, 0, item)
    
    const updated = [...kpis, ...graphs]
    set({ dashboardCharts: updated })
    try {
      const { saveDashboardConfig } = await import('../api/client')
      await saveDashboardConfig(fileId, { charts: updated })
    } catch {}
  },


  fetchConfig: async () => {
    try {
      // Lazy import client to avoid circular dependencies if store is used there
      const { getHealthConfig } = await import('../api/client')
      const res = await getHealthConfig()
      if (res?.config) {
        set({ config: res.config })
      }
    } catch { /* ignore */ }
  },

  setUploadResult: (res, fileName) => {
    // Close any in-flight WebSocket before loading new file state
    const ws = get().activeWs
    if (ws) { try { ws.close() } catch { /* ignore */ } }

    if (res.status === 'needs_sheet_selection') {
      set({
        status: 'needs_sheet',
        fileId: res.file_id,
        fileName,
        sheetNames: res.sheet_names ?? [],
        dashboardCharts: [],
        // Clear stale state from previous file
        activeWs: null,
        currentPromptId: null,
        chart: null,
        explanation: null,
        clarificationQuestion: null,
        errorMessage: null,
        lastPromptText: null,
      })
    } else {
      const columns = res.columns ?? []
      const previewRows = (res.preview_rows ?? []) as Record<string, unknown>[]
      set({
        status: 'previewing',
        fileId: res.file_id,
        fileName,
        rowCount: res.row_count ?? null,
        columns,
        previewRows,
        sheetNames: [],
        dashboardCharts: [],
        // Clear stale state from previous file
        activeWs: null,
        currentPromptId: null,
        chart: null,
        explanation: null,
        clarificationQuestion: null,
        errorMessage: null,
        lastPromptText: null,
      })
      // Persist to shared dataset store so switching pages doesn't require re-upload
      useDatasetStore.getState().addDataset({
        id: res.file_id,
        name: fileName,
        rowCount: res.row_count ?? 0,
        columns,
        previewRows,
        uploadedAt: new Date(),
      })
    }
  },

  setStatus: (s) => set({ status: s }),
  setPromptId: (id) => set({ currentPromptId: id }),
  setChart: (c, explanation) => set({ chart: c, explanation: explanation ?? null, status: 'completed' }),
  setClarification: (q) => set({ clarificationQuestion: q, status: 'awaiting_clarification' }),
  setError: (msg) => set({ errorMessage: msg, status: 'error' }),
  setLastPromptText: (text) => set({ lastPromptText: text }),

  setActiveWs: (ws) => {
    // Close previous socket before installing the new one
    const prev = get().activeWs
    if (prev && prev !== ws) {
      try { prev.close() } catch { /* ignore */ }
    }
    set({ activeWs: ws })
  },

  resetPrompt: () => {
    // Close any in-flight WebSocket before resetting prompt state
    const ws = get().activeWs
    if (ws) { try { ws.close() } catch { /* ignore */ } }
    set({
      activeWs: null,
      currentPromptId: null,
      chart: null,
      explanation: null,
      clarificationQuestion: null,
      errorMessage: null,
      status: 'previewing',
    })
  },

  resetAll: () => {
    // Full reset back to idle — used by "Nouveau fichier" instead of page reload
    const ws = get().activeWs
    if (ws) { try { ws.close() } catch { /* ignore */ } }

    useDatasetStore.getState().setActive(null)
    set({
      status: 'idle',
      activeWs: null,
      fileId: null,
      fileName: null,
      rowCount: null,
      columns: [],
      previewRows: [],
      sheetNames: [],
      dashboardCharts: [],
      currentPromptId: null,
      chart: null,
      explanation: null,
      clarificationQuestion: null,
      errorMessage: null,
    })
  },

  // Toast lifecycle is owned by <Toast> component (5 s timer) — store just holds the list
  addToast: (severity, message) => {
    const id = generateUUID()
    set((s) => ({ toasts: [...s.toasts, { id, severity, message }] }))
  },
  dismissToast: (id) =>
    set((s) => ({ toasts: s.toasts.filter((t) => t.id !== id) })),

  hydrateSession: async () => {
    try {
      const { fetchCurrentSession } = await import('../api/client')
      const session = await fetchCurrentSession()
      if (session && session.files && session.files.length > 0) {
        const validFiles = session.files.filter((f: any) => f.columns && f.columns.length > 0)

        // Hydrate datasetStore
        validFiles.forEach((f: any) => {
          useDatasetStore.getState().addDataset({
            id: f.id,
            name: f.name,
            rowCount: f.rowCount,
            columns: f.columns,
            previewRows: f.previewRows,
            uploadedAt: new Date(f.uploadedAt),
          })
        })

        if (validFiles.length > 0) {
          // Pick the latest valid file to make active
          const latestFile = validFiles[validFiles.length - 1]
          useDatasetStore.getState().setActive(latestFile.id)

          // Find prompts for this file
          const filePrompts = session.prompts.filter((p: any) => p.file_id === latestFile.id)
          const lastPrompt = filePrompts[filePrompts.length - 1]

          const configCharts = latestFile.dashboardConfig?.charts || []

          set({
            // Map backend 'failed' → frontend 'error'; backend never uses 'error' as a status string
            status: lastPrompt?.status === 'completed' ? 'completed' :
              lastPrompt?.status === 'awaiting_clarification' ? 'awaiting_clarification' :
                (lastPrompt?.status === 'failed' || lastPrompt?.status === 'error') ? 'error' : 'previewing',
            fileId: latestFile.id,
            fileName: latestFile.name,
            rowCount: latestFile.rowCount,
            columns: latestFile.columns,
            previewRows: latestFile.previewRows,
            dashboardCharts: configCharts,
            currentPromptId: lastPrompt?.id || null,
            lastPromptText: lastPrompt?.raw_text || null,
            clarificationQuestion: lastPrompt?.clarification_question || null,
            explanation: lastPrompt?.explanation || null,
            chart: lastPrompt?.chart || null,
            errorMessage: lastPrompt?.error_message || null,
          })
        }
      }
    } catch {
      /* ignore if not found or no backend */
    } finally {
      set({ isHydrating: false })
    }
  }
}))
