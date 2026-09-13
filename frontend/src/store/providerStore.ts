/**
 * providerStore.ts — Shared polling store for LLM provider status.
 *
 * Polls GET /api/v1/provider-status every 30 seconds so the whole app
 * has a single, consistent view of whether Ollama is reachable — no
 * per-component polling, no stale state between Badge and PromptBar.
 *
 * Usage:
 *   const { isOllamaOffline, ps } = useProviderStore()
 */
import { create } from 'zustand'
import { getProviderStatus } from '../api/client'
import type { ProviderStatus } from '../api/client'
import { getLLMConfig } from '../components/SettingsPanel'

const POLL_INTERVAL_MS = 30_000

interface ProviderState {
  ps:             ProviderStatus | null
  /** True only when the *active* provider is 'local' AND Ollama is not reachable. */
  isOllamaOffline: boolean
  /** Immediately re-fetch status (e.g. after the user saves new settings). */
  refresh: () => Promise<void>
  /** Start polling — called once at app bootstrap. */
  startPolling: () => () => void
}

export const useProviderStore = create<ProviderState>((set, get) => {
  async function fetchAndSet() {
    try {
      const d = await getProviderStatus()
      const cfg = getLLMConfig()
      const isLocal = (cfg.provider || d.provider) === 'local'
      set({
        ps: d,
        isOllamaOffline: isLocal && d.status !== 'online',
      })
    } catch {
      // Network error — treat Ollama as offline if local is the active provider
      const cfg = getLLMConfig()
      if (cfg.provider === 'local') {
        set(s => ({ ...s, isOllamaOffline: true }))
      }
    }
  }

  return {
    ps: null,
    isOllamaOffline: false,

    refresh: fetchAndSet,

    startPolling: () => {
      // Immediate first fetch
      fetchAndSet()
      const id = setInterval(fetchAndSet, POLL_INTERVAL_MS)
      return () => clearInterval(id)
    },
  }
})
