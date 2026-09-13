import React, { useState, useEffect } from 'react'
import { IconEye, IconEyeOff, IconLock, IconSettings, IconX, IconSparkle } from './Icon'
import { useProviderStore } from '../store/providerStore'

type Provider = 'openai' | 'anthropic' | 'google' | 'local'

interface LLMConfig {
  provider: Provider
  apiKey: string
  apiKeys: Record<string, string>
  model: string
}

const PROVIDERS: {
  value: Provider
  label: string
  tag: string
  models: string[]
  placeholder: string
}[] = [
  {
    value: 'openai',
    label: 'OpenAI',
    tag: 'GPT',
    models: ['gpt-4o', 'gpt-4o-mini', 'gpt-4-turbo', 'gpt-3.5-turbo'],
    placeholder: 'sk-...',
  },
  {
    value: 'anthropic',
    label: 'Anthropic',
    tag: 'Claude',
    models: ['claude-3-5-sonnet-20241022', 'claude-3-haiku-20240307', 'claude-3-opus-20240229'],
    placeholder: 'sk-ant-...',
  },
  {
    value: 'google',
    label: 'Google',
    tag: 'Gemini',
    models: ['gemini/gemini-3.5-flash', 'gemini/gemini-flash-latest'],
    placeholder: 'AIza...',
  },
  {
    value: 'local',
    label: 'Ollama',
    tag: 'Local',
    models: ['ollama/qwen2.5-coder:7b', 'ollama/qwen2.5-coder:14b', 'ollama/qwen3:8b', 'ollama/gemma4:latest'],
    placeholder: 'Aucune clé requise',
  },
]

const PROVIDER_LOGOS: Record<Provider, React.ReactNode> = {
  openai: (
    <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" style={{ marginRight: '6px', color: '#10a37f' }}>
      <path d="M12 2v20M2 12h20M5.64 5.64l12.72 12.72M5.64 18.36L18.36 5.64" />
      <circle cx="12" cy="12" r="3" fill="currentColor" />
    </svg>
  ),
  anthropic: (
    <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" style={{ marginRight: '6px', color: '#cc9966' }}>
      <path d="M4 20l4-16h8l4 16M6 12h12" />
    </svg>
  ),
  google: (
    <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" style={{ marginRight: '6px', color: '#4285f4' }}>
      <path d="M12 2c0 5.5-4.5 10-10 10 5.5 0 10 4.5 10 10 0-5.5 4.5-10 10-10-5.5 0-10-4.5-10-10z" fill="currentColor" />
    </svg>
  ),
  local: (
    <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" style={{ marginRight: '6px', color: '#6b7280' }}>
      <path d="M12 2L2 7l10 5 10-5-10-5zM2 17l10 5 10-5M2 12l10 5 10-5" />
    </svg>
  )
}

const PROVIDER_THEMES: Record<Provider, { primary: string; border: string; text: string; bg: string; bannerBorder: string; bannerText: string }> = {
  openai: {
    primary: '#10a37f',
    border: 'rgba(16, 163, 127, 0.15)',
    text: '#0d7d61',
    bg: '#f0fdf4',
    bannerBorder: '#bbf7d0',
    bannerText: '#15803d',
  },
  anthropic: {
    primary: '#d97706',
    border: 'rgba(217, 119, 6, 0.15)',
    text: '#b45309',
    bg: '#fffbeb',
    bannerBorder: '#fef3c7',
    bannerText: '#b45309',
  },
  google: {
    primary: '#4285f4',
    border: 'rgba(66, 133, 244, 0.15)',
    text: '#1a73e8',
    bg: '#eff6ff',
    bannerBorder: '#dbeafe',
    bannerText: '#1e40af',
  },
  local: {
    primary: '#4b5563',
    border: 'rgba(75, 85, 99, 0.15)',
    text: '#1f2937',
    bg: '#f9fafb',
    bannerBorder: '#e5e7eb',
    bannerText: '#374151',
  }
}

// Use sessionStorage (not localStorage) so the API key is scoped to this tab only.
// It is never written to disk, not shared across tabs, and is cleared on tab close.
// The session ID in client.ts stays in localStorage — that's not a secret.
const LS_KEY     = 'plateforme_llm_config'
const EXPL_KEY   = 'plateforme_explanation_mode'

export function getLLMConfig(): LLMConfig {
  try {
    const raw = sessionStorage.getItem(LS_KEY)
    if (raw) {
      const parsed = JSON.parse(raw)
      return { ...parsed, apiKeys: parsed.apiKeys || {} } as LLMConfig
    }
  } catch { /* ignore */ }
  return { provider: 'local', apiKey: '', apiKeys: {}, model: 'ollama/qwen2.5-coder:7b' }
}

/** Returns true if explanation mode is enabled.
 * Defaults ON for cloud providers (fast), OFF for local/Ollama (would triple latency).
 * User can override via the toggle in Settings. */
export function getExplanationMode(): boolean {
  const stored = sessionStorage.getItem(EXPL_KEY)
  if (stored !== null) return stored === 'true'   // explicit user choice always wins
  // Default: off (user can enable via Settings toggle)
  return false
}

function saveLLMConfig(cfg: LLMConfig) {
  sessionStorage.setItem(LS_KEY, JSON.stringify(cfg))
  window.dispatchEvent(new Event('llm-config-changed'))
}

// sessionStorage is automatically cleared by the browser when the tab is closed.
// We do NOT want to clear it on 'beforeunload', because that also triggers on 
// page refreshes, causing the user to lose their model selection.

const KEY_RULES: Partial<Record<Provider, { prefixes: string[], minLength: number }>> = {
  openai: { prefixes: ['sk-'], minLength: 40 },
  anthropic: { prefixes: ['sk-ant-'], minLength: 40 },
  google: { prefixes: ['AIza', 'AQ.'], minLength: 35 },
}

function getValidationState(provider: Provider, key: string) {
  if (provider === 'local') return 'valid';
  if (!key.trim()) return 'empty';
  
  const rule = KEY_RULES[provider];
  if (rule && rule.prefixes.some(p => key.startsWith(p)) && key.length >= rule.minLength) {
    return 'valid';
  }
  return 'invalid';
}

/** Explanation mode toggle — reads/writes EXPL_KEY in sessionStorage. */
function ExplanationToggle() {
  const [enabled, setEnabled] = React.useState(() => getExplanationMode())
  const toggle = () => {
    const next = !enabled
    setEnabled(next)
    sessionStorage.setItem(EXPL_KEY, String(next))
  }
  return (
    <div className="explanation-toggle" style={{ marginBottom: '14px' }}>
      <label className="explanation-toggle__label" htmlFor="explanation-toggle-cb">
        <input
          id="explanation-toggle-cb"
          type="checkbox"
          checked={enabled}
          onChange={toggle}
          className="explanation-toggle__cb"
        />
        <span>
          <strong>Explication automatique</strong>
          <span className="text-xs text-muted" style={{ display: 'block', marginTop: 2 }}>
            Génère une phrase d'explication après chaque graphique
            (un appel LLM supplémentaire par réponse).
          </span>
        </span>
      </label>
    </div>
  )
}

export function SettingsPanel({ onClose }: { onClose: () => void }) {
  const [cfg, setCfg] = useState<LLMConfig>(getLLMConfig)
  const [saving, setSaving] = useState(false)
  const [saved, setSaved] = useState(false)
  const [showKey, setShowKey] = useState(false)

  // Read Ollama status from the shared polling store — no separate fetch needed
  const { isOllamaOffline, ps } = useProviderStore()
  const ollamaStatus: 'checking' | 'online' | 'offline' =
    ps === null ? 'checking' : isOllamaOffline ? 'offline' : 'online'

  const providerMeta = PROVIDERS.find(p => p.value === cfg.provider)!
  const keyValidation = getValidationState(cfg.provider, cfg.apiKey)
  const theme = PROVIDER_THEMES[cfg.provider]

  const themeStyle = {
    '--provider-primary': theme.primary,
    '--provider-border': theme.border,
    '--provider-text': theme.text,
    '--provider-banner-bg': theme.bg,
    '--provider-banner-border': theme.bannerBorder,
    '--provider-banner-text': theme.bannerText,
  } as React.CSSProperties;

  function save() {
    // Block save if the key format is wrong (client-side guard)
    if (cfg.provider !== 'local' && keyValidation !== 'valid') return
    setSaving(true)
    setTimeout(() => {
      saveLLMConfig(cfg)
      setSaving(false)
      setSaved(true)
      setTimeout(() => {
        setSaved(false)
        onClose()
      }, 800)
    }, 600)
  }

  return (
    <div
      className="settings-backdrop"
      onClick={e => e.target === e.currentTarget && onClose()}
      role="dialog"
      aria-modal="true"
      aria-label="Paramètres du modèle IA"
    >
      <div className="settings-panel animate-scale-in" style={themeStyle}>

        {/* Header */}
        <div className="settings-panel__header">
          <div style={{ display: 'flex', alignItems: 'center', gap: 'var(--space-3)' }}>
            <div className="section-icon">
              <IconSettings size={14} strokeWidth={1.75} />
            </div>
            <div>
              <h3 style={{ margin: 0, fontSize: '15px', fontWeight: 600 }}>Modèle IA</h3>
              <p className="text-sm text-muted" style={{ margin: 0 }}>Fournisseur et clé API</p>
            </div>
          </div>
          
          <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
            <button
              className="btn btn--ghost btn--icon"
              onClick={onClose}
              aria-label="Fermer"
              style={{ color: 'var(--text-3)', width: '28px', height: '28px', borderRadius: '50%' }}
            >
              <IconX size={14} strokeWidth={2} />
            </button>
          </div>
        </div>

        <div className="settings-panel__body">
          {/* Privacy notice */}
          <div className="privacy-banner">
            <IconLock size={13} strokeWidth={2} />
            Votre clé est stockée uniquement dans le navigateur (sessionStorage, effacée à la fermeture de l'onglet).
          </div>

          {/* Provider selector */}
          <div style={{ marginBottom: '14px' }}>
            <p className="text-label" style={{ marginBottom: '8px' }}>Fournisseur</p>
            <div className="provider-grid">
              {PROVIDERS.map(p => (
                <button
                  key={p.value}
                  className={`provider-btn provider-btn--${p.value}${cfg.provider === p.value ? ' provider-btn--active' : ''}`}
                  onClick={() => setCfg(c => ({ 
                    ...c, 
                    provider: p.value, 
                    model: p.models[0], 
                    apiKey: c.apiKeys[p.value] || '' 
                  }))}
                  type="button"
                  id={`provider-${p.value}`}
                >
                  {PROVIDER_LOGOS[p.value]}
                  <span className="provider-btn__label">{p.label}</span>
                  {cfg.provider === p.value && (
                    <span className="provider-btn__check">✓</span>
                  )}
                </button>
              ))}
            </div>
          </div>

          <hr className="settings-divider" />

          {/* Model selector */}
          <div style={{ marginBottom: '14px' }}>
            <label htmlFor="model-select" className="text-label" style={{ display: 'block', marginBottom: '8px' }}>
              Modèle
            </label>
            <div className="select-wrapper">
              <span className="select-prefix">
                <IconSparkle size={14} strokeWidth={2} />
              </span>
              <select
                id="model-select"
                className="settings-select"
                value={cfg.model}
                onChange={e => setCfg(c => ({ ...c, model: e.target.value }))}
              >
                {providerMeta.models.map(m => (
                  <option key={m} value={m}>{m}</option>
                ))}
              </select>
            </div>

          </div>

          <hr className="settings-divider" />

          {/* API Key */}
          {cfg.provider !== 'local' && (
            <div style={{ marginBottom: '14px' }}>
              <label htmlFor="api-key-input" className="text-label" style={{ display: 'block', marginBottom: '8px' }}>
                Clé API
              </label>
              <div className="api-key-wrapper">
                <input
                  id="api-key-input"
                  type={showKey ? 'text' : 'password'}
                  className={`settings-input ${
                    keyValidation === 'valid' ? 'settings-input--valid' :
                    keyValidation === 'invalid' ? 'settings-input--invalid' : ''
                  }`}
                  placeholder={providerMeta.placeholder}
                  value={cfg.apiKey}
                  onChange={e => setCfg(c => ({ 
                    ...c, 
                    apiKey: e.target.value, 
                    apiKeys: { ...c.apiKeys, [c.provider]: e.target.value } 
                  }))}
                  autoComplete="off"
                  spellCheck={false}
                />
                <button
                  className={`api-key-toggle ${showKey ? 'api-key-toggle--active' : ''}`}
                  type="button"
                  onClick={() => setShowKey(v => !v)}
                  title={showKey ? 'Masquer' : 'Afficher'}
                >
                  {showKey
                    ? <IconEyeOff size={14} strokeWidth={1.75} />
                    : <IconEye    size={14} strokeWidth={1.75} />
                  }
                </button>
              </div>
              
              {keyValidation === 'valid' && (
                <p className="text-xs" style={{ color: '#16a34a', marginTop: '6px', display: 'flex', alignItems: 'center', gap: '4px' }}>
                  ✓ Clé au format valide pour {providerMeta.label}
                </p>
              )}
              {keyValidation === 'invalid' && (
                <p className="text-xs" style={{ color: '#ef4444', marginTop: '6px', display: 'flex', alignItems: 'center', gap: '4px' }}>
                  ⚠ Format de clé invalide
                </p>
              )}
              {keyValidation === 'empty' && (
                <p className="text-xs text-muted" style={{ marginTop: '6px' }}>
                  Obtenez votre clé sur{' '}
                  {cfg.provider === 'openai'    && <a href="https://platform.openai.com/api-keys"    target="_blank" rel="noreferrer">platform.openai.com</a>}
                  {cfg.provider === 'anthropic' && <a href="https://console.anthropic.com/"          target="_blank" rel="noreferrer">console.anthropic.com</a>}
                  {cfg.provider === 'google'    && <a href="https://aistudio.google.com/app/apikey"  target="_blank" rel="noreferrer">aistudio.google.com</a>}
                </p>
              )}
            </div>
          )}

          {/* Ollama instructions */}
          {cfg.provider === 'local' && (
            <div className="card--flat" style={{ padding: 'var(--space-4)', marginBottom: '14px', borderRadius: 'var(--radius-sm)' }}>

              {/* Live status row */}
              <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 'var(--space-3)' }}>
                {ollamaStatus === 'checking' && (
                  <><div className="spinner spinner--sm" /><span style={{ fontSize: 12, color: 'var(--text-2)' }}>Vérification…</span></>
                )}
                {ollamaStatus === 'online' && (
                  <div style={{ display: 'flex', alignItems: 'center', gap: 6, padding: '4px 10px', borderRadius: 20, background: 'rgba(22,163,74,0.1)', border: '1px solid rgba(22,163,74,0.25)' }}>
                    <span style={{ width: 8, height: 8, borderRadius: '50%', background: '#16a34a', display: 'inline-block' }} />
                    <span style={{ fontSize: 12, fontWeight: 600, color: '#16a34a' }}>Ollama en ligne</span>
                  </div>
                )}
                {ollamaStatus === 'offline' && (
                  <div style={{ display: 'flex', alignItems: 'center', gap: 6, padding: '4px 10px', borderRadius: 20, background: 'rgba(220,38,38,0.1)', border: '1px solid rgba(220,38,38,0.25)' }}>
                    <span style={{ width: 8, height: 8, borderRadius: '50%', background: '#dc2626', display: 'inline-block' }} />
                    <span style={{ fontSize: 12, fontWeight: 600, color: '#dc2626' }}>Ollama hors ligne — indisponible</span>
                  </div>
                )}
              </div>

              {ollamaStatus === 'offline' && (
                <p style={{ fontSize: 12, color: '#dc2626', marginBottom: 'var(--space-3)', lineHeight: 1.5 }}>
                  Ollama n'est pas accessible. Lancez-le avec les commandes ci-dessous, puis sélectionnez à nouveau ce fournisseur pour actualiser.
                </p>
              )}

              <p className="text-sm" style={{ color: 'var(--text-2)', marginBottom: 'var(--space-2)' }}>
                Pour utiliser Ollama localement :
              </p>
              <code className="code-block">ollama serve</code>
              <code className="code-block" style={{ marginTop: 'var(--space-2)' }}>
                ollama pull {(cfg.model.startsWith('ollama/') ? cfg.model.slice(7) : cfg.model) || 'qwen2.5-coder:7b'}
              </code>
            </div>
          )}

          {/* Explanation toggle */}
          <ExplanationToggle />

          {/* Save */}
          <button
            className="btn btn--primary"
            style={{ width: '100%', height: '38px', display: 'flex', alignItems: 'center', justifyContent: 'center', gap: '8px' }}
            onClick={save}
            disabled={saving || saved || (cfg.provider !== 'local' && keyValidation !== 'valid') || (cfg.provider === 'local' && ollamaStatus === 'offline')}
            title={
              cfg.provider === 'local' && ollamaStatus === 'offline'
                ? 'Ollama est hors ligne — impossible d\'enregistrer ce fournisseur'
                : cfg.provider !== 'local' && keyValidation !== 'valid'
                  ? 'Entrez une clé API valide pour pouvoir enregistrer'
                  : ''
            }
            id="save-settings-btn"
          >
            {saving ? (
              <>
                <div className="spinner spinner--sm spinner--inv" />
                Enregistrement...
              </>
            ) : saved ? (
              'Enregistré avec succès ✓'
            ) : (
              'Enregistrer'
            )}
          </button>
        </div>
      </div>
    </div>
  )
}
