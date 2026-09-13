/**
 * ProviderStatusBadge.tsx — Shows the active LLM provider and its status.
 *
 * Reads from the shared providerStore (polled every 30 s from App.tsx).
 * No per-component interval — single source of truth for the whole app.
 *
 * Dot colors:
 *   green  = Ollama online, or cloud provider configured
 *   amber  = Ollama offline but fallback available
 *   red    = Ollama offline, no fallback (user is blocked) — pulses
 */
import React from 'react'
import { useProviderStore } from '../store/providerStore'
import { getLLMConfig } from './SettingsPanel'

const LABELS: Record<string, string> = {
  local:     'Ollama',
  openai:    'OpenAI',
  anthropic: 'Claude',
  google:    'Gemini',
}

export function ProviderStatusBadge() {
  const { ps, isOllamaOffline } = useProviderStore()

  if (!ps) return null

  const activeProvider = getLLMConfig().provider || ps.provider
  const isLocal   = activeProvider === 'local'
  const isWarning = isLocal && isOllamaOffline && !!ps.fallback
  const isError   = isLocal && isOllamaOffline && !ps.fallback

  const dotClass = isError
    ? 'provider-dot provider-dot--red'
    : isWarning
      ? 'provider-dot provider-dot--amber'
      : isLocal
        ? 'provider-dot provider-dot--local-online'   // green when Ollama is confirmed online
        : `provider-dot provider-dot--${activeProvider}`

  const label = LABELS[activeProvider] ?? activeProvider

  let tooltip: string
  if (isError) {
    tooltip = `${label} hors ligne — les requêtes ne peuvent pas être traitées`
  } else if (isWarning) {
    tooltip = `${label} hors ligne — bascule vers ${ps.fallback}`
  } else if (isLocal) {
    tooltip = `${label} · ${ps.model}`
  } else {
    tooltip = `${label} · ${getLLMConfig().model}`
  }

  return (
    <div
      id="provider-status-badge"
      className={`provider-badge${isError ? ' provider-badge--error' : ''}`}
      title={tooltip}
      aria-label={`Modèle IA : ${tooltip}`}
    >
      <span className={dotClass} aria-hidden="true" />
      <span className="provider-badge__label">
        {isError   ? `${label} · Hors ligne` :
         isWarning ? `${label} → Gemini`     : label}
      </span>
    </div>
  )
}
