# coding: utf-8
import io
with io.open(r'c:\Users\r3d4\.gemini\antigravity-ide\scratch\plateforme-restitution\frontend\src\App.tsx', 'w', encoding='utf-8') as f:
    f.write('''import React, { useState, useEffect } from 'react'
import 'react-grid-layout/css/styles.css'
import 'react-resizable/css/styles.css'
import { useStore } from './store'
import { useDatasetStore } from './store/datasetStore'
import { UploadPage } from './pages/UploadPage'
import { AdminPage } from './pages/AdminPage'
import { LandingPage } from './pages/LandingPage'
import { useKeycloak } from './auth/KeycloakProvider'

const DashboardPage = React.lazy(() => import('./pages/DashboardPage').then(module => ({ default: module.DashboardPage })))
const AskiPage = React.lazy(() => import('./pages/AskiPage').then(module => ({ default: module.AskiPage })))
import { ToastContainer } from './components/StatusToast'
import { SettingsPanel, getLLMConfig } from './components/SettingsPanel'
import { ProviderStatusBadge } from './components/ProviderStatusBadge'
import { openPromptSocket } from './api/client'
import type { WsEvent } from './api/types'
import {
  IconActivity,
  IconSettings,
  IconFile,
} from './components/Icon'
import { UserMenu } from './components/UserMenu'

type Page = 'upload' | 'aski' | 'dashboard' | 'admin'

export default function App() {
  const { keycloak, initialized } = useKeycloak()
  const isAuthenticated = keycloak?.authenticated || false
  const isAdmin = keycloak?.realmAccess?.roles.includes('admin') || false

  const { 
    fileName, resetAll, fetchConfig, hydrateSession, isHydrating,
    currentPromptId, status, setStatus, setChart, addToast, setClarification, setError, setActiveWs
  } = useStore()
  const { datasets, activeId, setActive } = useDatasetStore()

  const [page, setPage] = useState<Page>(() => {
    const saved = sessionStorage.getItem('clarIA_page') as Page | null
    return (saved && ['upload', 'aski', 'dashboard', 'admin'].includes(saved)) ? saved : 'upload'
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

  useEffect(() => {
    if (!hasDatasets && page !== 'upload' && page !== 'admin' && initialHydrated) {
      setPage('upload')
    }
  }, [hasDatasets, page, initialHydrated])

  useEffect(() => {
    sessionStorage.setItem('clarIA_page', page)
  }, [page])

  useEffect(() => {
    if (!currentPromptId || !['processing', 'prompting'].includes(status)) return

    const ws = openPromptSocket(currentPromptId)
    let terminated = false

    const terminate = () => {
      if (!terminated) {
        terminated = true
        ws.close()
        setActiveWs(null)
      }
    }

    ws.onmessage = (msg) => {
      try {
        const event = JSON.parse(msg.data)
        if (event.status === 'processing' || event.status === 'pending') {
          setStatus('processing')
        } else if (event.status === 'completed') {
          setChart(event.chart, event.explanation)
          addToast('success', 'Reponse generee avec succes.')
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

    ws.onerror = () => { }

    ws.onclose = () => {
      if (!terminated && useStore.getState().status === 'processing') {
        addToast('error', 'Connexion interrompue. Reessayez.')
        setStatus('previewing')
      }
    }

    setActiveWs(ws)

    return () => {
      if (!terminated) {
        ws.close()
        setActiveWs(null)
      }
    }
  }, [currentPromptId])

  const handleOpenDashboard = (datasetId) => {
    setActive(datasetId)
    setPage('dashboard')
  }
  const handleOpenAski = (datasetId) => {
    setActive(datasetId)
    setPage('aski')
  }

  const llmCfg = getLLMConfig()
  const providerLabel = {
    openai: 'OpenAI', anthropic: 'Claude',
    google: 'Gemini', local: 'Ollama',
  }
  const providerName = providerLabel[llmCfg.provider] ?? llmCfg.provider

  const activeDataset = datasets.find(d => d.id === activeId)

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

  useEffect(() => {
    document.documentElement.setAttribute('data-provider', llmCfg.provider || 'local')
    const handler = () => {
      const cfg = getLLMConfig()
      document.documentElement.setAttribute('data-provider', cfg.provider || 'local')
    }
    window.addEventListener('llm-config-changed', handler)
    return () => window.removeEventListener('llm-config-changed', handler)
  }, [])

  if (!initialized) {
    return (
      <div style={{ display: 'flex', height: '100vh', alignItems: 'center', justifyContent: 'center' }}>
        <div className="spinner spinner--lg" />
      </div>
    )
  }

  if (!isAuthenticated) {
    return <LandingPage />
  }

  return (
    <div className="app">

      {/* Header */}
      <header className="app-header">
        <div className="app-header__inner">
          {/* Brand */}
          <div className="app-header__brand" style={{ cursor: 'pointer' }} onClick={() => setPage('upload')}>
            <div className="app-header__logo">
              <IconActivity size={18} strokeWidth={2.5} />
            </div>
            <div className="app-header__name">ClarIA</div>
          </div>

          {/* Center Title for Admins */}
          {isAdmin && page === 'admin' ? (
            <div style={{ fontWeight: 600, fontSize: '15px', color: 'var(--text-1)', textAlign: 'center' }}>
              Administration
            </div>
          ) : (
            <nav className="app-nav" aria-label="Navigation principale">
              <button
                id="nav-upload"
                className={
av-tab}
                onClick={() => setPage('upload')}
                aria-current={page === 'upload' ? 'page' : undefined}
              >
                Accueil
              </button>
              <div className={
av-tabs-group } aria-hidden={!hasActiveFile}>
                <button
                  id="nav-dashboard"
                  className={
av-tab}
                  onClick={() => setPage('dashboard')}
                  aria-current={page === 'dashboard' ? 'page' : undefined}
                  tabIndex={hasActiveFile ? 0 : -1}
                >
                  Dashboard
                </button>
                <button
                  id="nav-aski"
                  className={
av-tab}
                  onClick={() => setPage('aski')}
                  aria-current={page === 'aski' ? 'page' : undefined}
                  tabIndex={hasActiveFile ? 0 : -1}
                >
                  Aski
                </button>
              </div>
            </nav>
          )}

          {/* Right controls */}
          <div className="app-header__right">
            {!(isAdmin && page === 'admin') && <div className="app-header__divider" aria-hidden="true" />}
            
            {!(isAdmin && page === 'admin') && fileName && (
              <div className="file-chip" title={fileName}>
                <span className="file-chip__icon">
                  <IconFile size={13} strokeWidth={2} />
                </span>
                {fileName}
              </div>
            )}
            
            {!(isAdmin && page === 'admin') && <ProviderStatusBadge />}
            
            {!(isAdmin && page === 'admin') && (
              <button
                id="settings-btn"
                className="btn btn--ghost btn--icon"
                onClick={() => setShowSettings(true)}
                title="Configurer le modele IA"
                aria-label="Configurer le modele IA"
              ><IconSettings size={16} strokeWidth={1.75} /></button>
            )}

            {(isAdmin && page === 'admin') && <div className="app-header__divider" aria-hidden="true" />}
            
            <UserMenu onNavigate={isAdmin ? (newPage) => setPage(newPage) : undefined} />
          </div>
        </div>
      </header>

      {/* Main */}
      <main className={pp-main } id="main-content">
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
              {page === 'admin' && isAdmin && <AdminPage />}
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
''')
