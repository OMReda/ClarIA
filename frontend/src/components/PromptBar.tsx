import React, { useEffect, useState } from 'react'
import { MessageSquare } from 'lucide-react'
import { openPromptSocket, submitPrompt } from '../api/client'
import { useStore } from '../store'
import type { WsEvent } from '../api/types'

export function PromptBar() {
  const [text, setText] = useState('')
  const {
    fileId, status, lastPromptText,
    setPromptId, setChart, setClarification, setError, setStatus, addToast,
    setActiveWs, setLastPromptText
  } = useStore()
  const isProcessing = status === 'processing' || status === 'prompting'
  const canSubmit = !!fileId && !isProcessing && ['previewing', 'completed', 'error'].includes(status)

  // Restore previous prompt when entering previewing state (e.g. after clicking Retry)
  useEffect(() => {
    if (status === 'previewing' && lastPromptText) {
      setText(lastPromptText)
      setLastPromptText(null)
    }
  }, [status, lastPromptText, setLastPromptText])

  useEffect(() => {
    const handleRetry = () => {
      if (lastPromptText && fileId) {
        setText(lastPromptText)
        executeSubmit(lastPromptText)
      }
    }
    window.addEventListener('trigger-retry', handleRetry)
    return () => window.removeEventListener('trigger-retry', handleRetry)
  }, [lastPromptText, fileId])

  const executeSubmit = async (promptText: string) => {
    if (!promptText || !fileId) return

    setPromptId(null)
    setChart(null)
    setClarification(null)
    setError(null)
    setStatus('prompting')

    try {
      const { prompt_id } = await submitPrompt(fileId, promptText)
      setPromptId(prompt_id)
      setLastPromptText(promptText)
      setText('')
    } catch (err: any) {
      const apiErrorMsg = err.response?.data?.detail?.error?.message;
      const displayMsg = apiErrorMsg || err.message || "Erreur de connexion.";
      setError(displayMsg)
      addToast('error', displayMsg)
      setStatus('error')
    }
  }

  const submit = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!text.trim() || !canSubmit) return
    executeSubmit(text.trim())
  }

  return (
    <form className="card prompt-bar" onSubmit={submit} id="prompt-form" aria-label="Formulaire de question">
      <div className="section-header">
        <div className="section-icon" aria-hidden="true">
          <MessageSquare size={16} strokeWidth={2} />
        </div>
        <div style={{ flex: 1 }}>
          <p className="section-header__title">Posez votre question</p>
          <p className="section-header__sub">Posez une question sur vos données — graphique, résumé ou statistique</p>
        </div>
      </div>

      <div className="prompt-bar__body">
        <div className="prompt-bar__inner">
          <textarea
            id="prompt-input"
            className="prompt-input"
            placeholder="Ex : Montre l'évolution des ventes par mois sous forme de courbe…"
            value={text}
            onChange={(e) => setText(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); submit(e as any) }
            }}
            disabled={!canSubmit}
            rows={2}
            maxLength={2000}
            aria-label="Description de la demande"
            // eslint-disable-next-line jsx-a11y/no-autofocus
            autoFocus
          />
          <button
            type="submit"
            id="send-prompt-btn"
            className="btn btn--primary btn--icon"
            disabled={!canSubmit || !text.trim()}
            aria-label="Envoyer"
            title="Envoyer (Entrée)"
          >
            {isProcessing
              ? <span className="spinner spinner--sm spinner--inv" />
              : (
                <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                  <line x1="22" y1="2" x2="11" y2="13"/><polygon points="22 2 15 22 11 13 2 9 22 2"/>
                </svg>
              )
            }
          </button>
        </div>

        {isProcessing ? (
          <div className="processing-row" style={{ marginTop: 'var(--space-3)' }}>
            <div className="spinner spinner--sm" />
            <span className="processing-text">Analyse en cours</span>
          </div>
        ) : (
          <p className="prompt-bar__hint">
            Appuyez sur <kbd className="kbd">Entrée</kbd> pour envoyer · <kbd className="kbd">Maj+Entrée</kbd> pour un saut de ligne
          </p>
        )}
      </div>
    </form>
  )
}
