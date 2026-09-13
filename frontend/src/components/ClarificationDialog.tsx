import React, { useState } from 'react'
import { clarifyPrompt, openPromptSocket } from '../api/client'
import { MessageCircleQuestion } from 'lucide-react'
import { useStore } from '../store'

export function ClarificationDialog() {
  const {
    clarificationQuestion, currentPromptId,
    addToast, setStatus, setClarification, setChart, setError,
    setActiveWs,
  } = useStore()
  const [answer, setAnswer] = useState('')
  const [loading, setLoading] = useState(false)

  if (!clarificationQuestion || !currentPromptId) return null

  async function submit(e: React.FormEvent) {
    e.preventDefault()
    if (!answer.trim() || loading) return
    setLoading(true)
    try {
      await clarifyPrompt(currentPromptId!, answer.trim())
      setStatus('processing')
      setAnswer('')

      // Open a new WebSocket for the re-run.
      // setActiveWs will close the old PromptBar socket before registering this one.
      const ws = await openPromptSocket(currentPromptId!)
      ws.onmessage = (ev) => {
        try {
          const event = JSON.parse(ev.data)
          if (event.status === 'completed') { setChart(event.chart, event.explanation); addToast('success', 'Graphique généré avec succès.') }
          else if (event.status === 'awaiting_clarification') setClarification(event.clarification_question)
          else if (event.status === 'failed') { setError(event.message); addToast('error', event.message) }
        } catch { /* ignore */ }
      }
      setActiveWs(ws)
    } catch {
      addToast('error', 'Erreur lors de l\'envoi de la réponse.')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div
      className="clarification-dialog"
      id="clarification-dialog"
      role="dialog"
      aria-label="Question de précision"
      aria-modal="true"
    >
      <div className="clarification-dialog__header">
        <div className="clarification-dialog__icon" aria-hidden="true">
          <MessageCircleQuestion size={20} />
        </div>
        <div>
          <p className="clarification-dialog__title">Une précision est nécessaire</p>
          <p className="clarification-dialog__question">{clarificationQuestion}</p>
        </div>
      </div>

      <form onSubmit={submit} className="clarification-dialog__form">
        <input
          id="clarification-input"
          type="text"
          className="clarification-input"
          placeholder="Votre réponse…"
          value={answer}
          onChange={(e) => setAnswer(e.target.value)}
          autoFocus
          disabled={loading}
          aria-label="Réponse à la question de précision"
          onKeyDown={(e) => e.key === 'Enter' && submit(e as any)}
        />
        <button
          type="submit"
          id="clarify-submit-btn"
          className="btn btn--primary"
          disabled={!answer.trim() || loading}
        >
          {loading
            ? <><span className="spinner spinner--sm spinner--inv" /> Envoi…</>
            : 'Confirmer'
          }
        </button>
      </form>
    </div>
  )
}
