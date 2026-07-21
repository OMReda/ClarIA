/**
 * ProviderStatusBadge.tsx — Shows the active LLM provider and its status.
 *
 * Polls GET /api/v1/provider-status once on mount.
 * Displays a colored dot: green=online/configured, amber=offline+fallback, red=offline.
 */
import React, { useEffect, useState } from 'react'
import { getProviderStatus } from '../api/client'
import type { ProviderStatus } from '../api/client'
import { getLLMConfig } from './SettingsPanel'

const LABELS: Record<string, string> = {
  local:     'Ollama',
  openai:    'OpenAI',
  anthropic: 'Claude',
  google:    'Gemini',
}

export function ProviderStatusBadge() {
  const [ps, setPs] = useState<ProviderStatus | null>(null)
  const [localCfg, setLocalCfg] = useState(() => getLLMConfig())

  useEffect(() => {
    let cancelled = false
    getProviderStatus().then((d) => { if (!cancelled) setPs(d) }).catch(() => {})
    return () => { cancelled = true }
  }, [])

  useEffect(() => {
    const onChange = () => setLocalCfg(getLLMConfig())
    window.addEventListener('llm-config-changed', onChange)
    return () => window.removeEventListener('llm-config-changed', onChange)
  }, [])

  if (!ps) return null

  const activeProvider = localCfg.provider || ps.provider

  // Determine dot color based on active provider
  const isLocal   = activeProvider === 'local'
  const isGood    = !isLocal || (ps.status === 'online' || ps.status === 'configured')
  const isWarning = isLocal && ps.status === 'offline' && !!ps.fallback
  const isError   = isLocal && ps.status === 'offline' && !ps.fallback

  const dotClass = isError
    ? 'provider-dot provider-dot--red'
    : isWarning
      ? 'provider-dot provider-dot--amber'
      : `provider-dot provider-dot--${activeProvider}`

  const label   = LABELS[activeProvider] ?? activeProvider
  const tooltip = isWarning
    ? `${label} hors ligne — bascule vers ${ps.fallback}`
    : isError
      ? `${label} hors ligne`
      : `${label} · ${isLocal ? ps.model : localCfg.model}`

  return (
    <div
      id="provider-status-badge"
      className="provider-badge"
      title={tooltip}
      aria-label={`Modèle IA : ${tooltip}`}
    >
      <span className={dotClass} aria-hidden="true" />
      <span className="provider-badge__label">
        {isWarning ? `${label} → Gemini` : label}
      </span>
    </div>
  )
}
