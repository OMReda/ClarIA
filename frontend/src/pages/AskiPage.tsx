/**
 * AskiPage.tsx — Conversational AI chart generation.
 *
 * This is the current single-page Aski experience extracted into its own
 * page component.  The full conversation flow (Stage 6) will be added here.
 * For now it renders the existing workspace: PreviewPanel + PromptBar +
 * ChartDisplay + ClarificationDialog.
 *
 * The page receives the active dataset via props (set by the router in App.tsx)
 * and loads it into AppState when it changes.
 */
import React, { useEffect } from 'react'
import { useStore } from '../store'
import { useDatasetStore } from '../store/datasetStore'
import { PreviewPanel } from '../components/PreviewPanel'
import { PromptBar } from '../components/PromptBar'
import { ChartDisplay } from '../components/ChartDisplay'
import { ClarificationDialog } from '../components/ClarificationDialog'
import { IconWarning } from '../components/Icon'

export function AskiPage() {
  const {
    status, errorMessage, chart,
    resetPrompt, resetAll,
    fileId, fileName,
  } = useStore()

  const { getActive } = useDatasetStore()
  const activeDs = getActive()



  // No dataset available
  if (!activeDs) {
    return (
      <div className="aski-empty animate-fade-up">
        <div className="aski-empty__inner">
          <p className="aski-empty__text">
            Aucun fichier sélectionné. Importez un fichier depuis la page d'accueil.
          </p>
        </div>
      </div>
    )
  }

  // Show the chart panel when:
  // - A request is in-flight (processing / prompting) so the loading spinner card is visible
  // - A chart is available in completed or previewing states
  const showChart   = status === 'processing' || status === 'prompting' || (!!chart && (status === 'completed' || status === 'previewing'))
  const showClarify = status === 'awaiting_clarification'

  return (
    <div className="workspace animate-fade-up">

      {/* 1. Preview Card */}
      <div className="card">
        <PreviewPanel />
      </div>

      {/* 2. Clarification dialog */}
      {showClarify && (
        <div className="card clarification-dialog">
          <ClarificationDialog />
        </div>
      )}

      {/* 3. Chart/Result Card */}
      {showChart && (
        <div className="card">
          <ChartDisplay />
        </div>
      )}

      {/* Error */}
      {status === 'error' && (
        <div className="card animate-fade-up" id="error-card">
          <div className="error-card" role="alert">
            <div className="error-card__icon">
              <IconWarning size={20} strokeWidth={1.75} />
            </div>
            <div className="error-card__body">
              <p className="error-card__title">Une erreur est survenue</p>
              <p className="error-card__message">
                {errorMessage ?? 'Impossible de générer le graphique.'}
              </p>
            </div>
            <button className="btn btn--ghost btn--sm" id="retry-btn" onClick={() => {
              window.dispatchEvent(new Event('trigger-retry'))
            }}>
              Réessayer
            </button>
          </div>
        </div>
      )}

      {/* Re-prompt */}
      {status === 'completed' && (
        <div className="reprompt-hint animate-fade-in">
          <button id="new-prompt-btn" className="btn btn--ghost btn--sm" onClick={resetPrompt}>
            ← Poser une autre question sur ce fichier
          </button>
        </div>
      )}

      {/* 4. Prompt Input */}
      <PromptBar />
    </div>
  )
}
