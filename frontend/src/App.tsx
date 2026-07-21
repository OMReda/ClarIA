import React, { useState, useEffect } from 'react'
import 'react-grid-layout/css/styles.css'
import 'react-resizable/css/styles.css'
import { useStore } from './store'
import { useDatasetStore } from './store/datasetStore'
import { UploadPage } from './pages/UploadPage'

const DashboardPage = React.lazy(() => import('./pages/DashboardPage').then(module => ({ default: module.DashboardPage })))
const AskiPage = React.lazy(() => import('./pages/AskiPage').then(module => ({ default: module.AskiPage })))
import { ToastContainer } from './components/StatusToast'
import { SettingsPanel, getLLMConfig } from './components/SettingsPanel'
import { ProviderStatusBadge } from './components/ProviderStatusBadge'
import { openPromptSocket } from './api/client'
import type { WsEvent } from './api/types'
import {
  IconBarChart,
  IconSettings,
  IconFile,
} from './components/Icon'

/** App-level page state — no external router dependency */
type Page = 'upload' | 'aski' | 'dashboard'

export default function App() {
  const { 
    fileName, resetAll, fetchConfig, hydrateSession, isHydrating,
    currentPromptId, status, setStatus, setChart, addToast, setClarification, setError, setActiveWs
  } = useStore()
  const { datasets, activeId, setActive } = useDatasetStore()

  const [page, setPage] = useState<Page>(() => {
    // Restore the current page from sessionStorage on refresh.
    // Falls back to 'upload' if no value is stored or an invalid value is found.
    const saved = sessionStorage.getItem('clarIA_page') as Page | null
    return (saved && ['upload', 'aski', 'dashboard'].includes(saved)) ? saved : 'upload'
  })
  const [showSettings, setShowSettings] = useState(false)
  const [initialHydrated, setInitialHydrated] = useState(false)

  const hasActiveFile = activeId !== null
  const hasDatasets = datasets.length > 0

  useEffect(() => { fetchConfig() }, [fetchConfig])
  useEffect(() => { hydrateSession() }, [hydrateSession])

  useEffect(() => {
    if (!isHydrating && !initialHydrated) {
      setInitialHydrated(true)
    }
  }, [isHydrating, initialHydrated])

  // Reset to upload page if the last dataset is deleted while not on it
  useEffect(() => {
    if (!hasDatasets && page !== 'upload' && initialHydrated) {
      setPage('upload')
    }
  }, [hasDatasets, page, initialHydrated])

  // Persist page choice so a browser refresh lands on the same tab
  useEffect(() => {
    sessionStorage.setItem('clarIA_page', page)
  }, [page])

  // Global WebSocket listener for background persistence (Issue 24)
  useEffect(() => {
    if (!currentPromptId || !['processing', 'prompting'].includes(status)) return

    const ws = openPromptSocket(currentPromptId)
    let terminated = false

    const terminate = () => {
      if (!terminated) {
        terminated = true
        ws.close() // Proactively close the underlying socket
        setActiveWs(null)
      }
    }

    ws.onmessage = (msg) => {
      try {
        const event: WsEvent = JSON.parse(msg.data)
        if (event.status === 'processing' || event.status === 'pending') {
          setStatus('processing')
        } else if (event.status === 'completed') {
          setChart(event.chart, event.explanation)
          addToast('success', 'Réponse générée avec succès.')
          terminate()
        } else if (event.status === 'awaiting_clarification') {
          setClarification(event.clarification_question)
          terminate()
        } else if (event.status === 'failed') {
          setError(event.message)
          addToast('error', event.message)
          terminate()
        }
      } catch { /* ignore malformed frames */ }
    }

    ws.onerror = () => { /* handled by onclose */ }

    ws.onclose = () => {
      if (!terminated && useStore.getState().status === 'processing') {
        addToast('error', 'Connexion interrompue. Réessayez.')
        setStatus('previewing')
      }
    }

    setActiveWs(ws)

    // Only cleanup if App unmounts (rare) or promptId changes
    return () => {
      if (!terminated) {
        ws.close()
        setActiveWs(null)
      }
    }
  }, [currentPromptId]) // Intentionally not including status/setChart etc. to avoid reconnect loops

  /* When the user clicks "Open in Dashboard/Aski" from the dataset list */
  const handleOpenDashboard = (datasetId: string) => {
    setActive(datasetId)
    setPage('dashboard')
  }
  const handleOpenAski = (datasetId: string) => {
    setActive(datasetId)
    setPage('aski')
  }

  const llmCfg = getLLMConfig()
  const providerLabel: Record<string, string> = {
    openai: 'OpenAI', anthropic: 'Claude',
    google: 'Gemini', local: 'Ollama',
  }
  const providerName = providerLabel[llmCfg.provider] ?? llmCfg.provider

  const activeDataset = datasets.find(d => d.id === activeId)

  // Re-sync AppState whenever the active dataset changes (e.g., from SheetSelector)
  useEffect(() => {
    if (!activeDataset) {
      useStore.setState({ fileName: null, fileId: null, dashboardCharts: [] })
      return
    }
    const currentStore = useStore.getState()
    if (currentStore.fileId !== activeDataset.id) {
      useStore.setState({
        status: 'previewing',
        fileId: activeDataset.id,
        fileName: activeDataset.name,
        rowCount: activeDataset.rowCount,
        columns: activeDataset.columns,
        previewRows: activeDataset.previewRows,
        sheetNames: [],
        currentPromptId: null,
        chart: null,
        clarificationQuestion: null,
        errorMessage: null,
        dashboardCharts: [],
      })
      useStore.getState().loadDashboardConfig()
    }
  }, [activeDataset])

  // Re-apply provider theme whenever config changes (storage key: llm-config)
  useEffect(() => {
    document.documentElement.setAttribute('data-provider', llmCfg.provider || 'local')
    const handler = () => {
      const cfg = getLLMConfig()
      document.documentElement.setAttribute('data-provider', cfg.provider || 'local')
    }
    window.addEventListener('llm-config-changed', handler)
    return () => window.removeEventListener('llm-config-changed', handler)
  }, [])


  return (
    <div className="app">

      {/* ── Header ──────────────────────────────────────────────────────────── */}
      <header className="app-header">
        <div className="app-header__inner">
          {/* Brand */}
          <div className="app-header__brand">
            <div className="app-header__logo" aria-hidden="true">
              <IconBarChart size={16} strokeWidth={2.25} />
            </div>
            <span className="app-header__name">ClarIA</span>
          </div>

          {/* Nav tabs */}
          <nav className="app-nav" aria-label="Navigation principale">
            <button
              id="nav-upload"
              className={`nav-tab${page === 'upload' ? ' nav-tab--active' : ''}`}
              onClick={() => {
                setPage('upload')
              }}
              aria-current={page === 'upload' ? 'page' : undefined}
            >
              Accueil
            </button>
            <div className={`nav-tabs-group ${hasActiveFile ? 'is-visible' : 'is-hidden'}`} aria-hidden={!hasActiveFile}>
              <button
                id="nav-dashboard"
                className={`nav-tab${page === 'dashboard' ? ' nav-tab--active' : ''}`}
                onClick={() => setPage('dashboard')}
                aria-current={page === 'dashboard' ? 'page' : undefined}
                tabIndex={hasActiveFile ? 0 : -1}
              >
                Dashboard
              </button>
              <button
                id="nav-aski"
                className={`nav-tab${page === 'aski' ? ' nav-tab--active' : ''}`}
                onClick={() => setPage('aski')}
                aria-current={page === 'aski' ? 'page' : undefined}
                tabIndex={hasActiveFile ? 0 : -1}
              >
                Aski
              </button>
            </div>
          </nav>

          {/* Right controls */}
          <div className="app-header__right">
            <div className="app-header__divider" aria-hidden="true" />
            {fileName && (
              <div className="file-chip" title={fileName}>
                <span className="file-chip__icon">
                  <IconFile size={13} strokeWidth={2} />
                </span>
                {fileName}
              </div>
            )}
            <ProviderStatusBadge />
            <button
              id="settings-btn"
              className="btn btn--ghost btn--icon"
              onClick={() => setShowSettings(true)}
              title="Configurer le modèle IA"
              aria-label="Configurer le modèle IA"
            ><IconSettings size={16} strokeWidth={1.75} /></button>
          </div>
        </div>
      </header>

      {/* ── Main ────────────────────────────────────────────────────────────── */}
      <main className={`app-main ${page === 'dashboard' ? 'app-main--dashboard' : ''}`} id="main-content">
        {isHydrating ? (
          <div style={{ display: 'flex', height: '100%', alignItems: 'center', justifyContent: 'center', color: 'var(--text-tertiary)' }}>
            <div className="skeleton-box" style={{ width: 120, height: 24, borderRadius: 4 }} />
          </div>
        ) : (
          <div className="page-transition" key={page}>
            {page === 'upload' && (
              <UploadPage
                onOpenDashboard={handleOpenDashboard}
                onOpenAski={handleOpenAski}
              />
            )}
            <React.Suspense fallback={
              <div style={{ display: 'flex', height: '100%', alignItems: 'center', justifyContent: 'center', color: 'var(--text-tertiary)' }}>
                <div className="skeleton-box" style={{ width: 120, height: 24, borderRadius: 4 }} />
              </div>
            }>
              {page === 'dashboard' && <DashboardPage />}
              {page === 'aski'      && <AskiPage />}
            </React.Suspense>
          </div>
        )}
      </main>

      {showSettings && (
        <SettingsPanel onClose={() => setShowSettings(false)} />
      )}

      <ToastContainer />
    </div>
  )
}
