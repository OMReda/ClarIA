import axios from 'axios'
import { FileUploadResponseSchema, FileDataResponseSchema } from './types'
import type { FileUploadResponse, FileDataResponse } from './types'
import { getLLMConfig, getExplanationMode } from '../components/SettingsPanel'
import { generateUUID } from '../utils/uuid'
import { keycloak } from '../auth/KeycloakProvider'

const SESSION_KEY = 'plateforme_session_id'

let sessionId = localStorage.getItem(SESSION_KEY)
if (!sessionId) {
  sessionId = generateUUID()
  localStorage.setItem(SESSION_KEY, sessionId)
}

const api = axios.create({
  baseURL: '/api/v1',
  headers: { 'Content-Type': 'application/json' },
})

// Inject session ID and Keycloak Bearer Token
api.interceptors.request.use(async (config) => {
  config.headers['X-Session-ID'] = sessionId

  if (keycloak && keycloak.authenticated && keycloak.token) {
    // If the token is about to expire, try to update it before sending the request
    try {
      await keycloak.updateToken(30)
      config.headers['Authorization'] = `Bearer ${keycloak.token}`
    } catch (error) {
      console.warn("Failed to refresh token", error)
      keycloak.login()
    }
  }

  return config
})

/**
 * Returns LLM config headers.
 * Attached explicitly only to submitPrompt and clarifyPrompt — never to file
 * upload / sheet-select / status-poll calls, where the API key is not used.
 */
function llmHeaders(): Record<string, string> {
  const llm = getLLMConfig()
  const headers: Record<string, string> = {
    'X-LLM-Provider': llm.provider,
    'X-LLM-Model':    llm.model,
  }
  if (llm.apiKey) headers['X-API-Key'] = llm.apiKey
  if (getExplanationMode()) headers['X-Explain'] = 'true'
  return headers
}

// ── File endpoints ────────────────────────────────────────────────────────────

export async function uploadFile(file: File): Promise<FileUploadResponse> {
  const form = new FormData()
  form.append('file', file)
  const { data } = await api.post('/files', form, {
    headers: { 'Content-Type': 'multipart/form-data' },
  })
  return FileUploadResponseSchema.parse(data)
}

export async function selectSheet(
  fileId: string,
  sheetName: string
): Promise<FileUploadResponse> {
  const { data } = await api.post(`/files/${fileId}/sheet`, { sheet_name: sheetName })
  return FileUploadResponseSchema.parse(data)
}

export async function deleteFileAPI(fileId: string): Promise<void> {
  await api.delete(`/files/${fileId}`)
}

export async function getFileData(fileId: string): Promise<FileDataResponse> {
  const { data } = await api.get(`/files/${fileId}/data`)
  return FileDataResponseSchema.parse(data)
}

export async function getDashboardConfig(
  fileId: string
): Promise<Record<string, any>> {
  const { data } = await api.get(`/files/${fileId}/dashboard-config`, {
    params: { _t: Date.now() }
  })
  return data.dashboard_config || {}
}

export async function saveDashboardConfig(
  fileId: string,
  config: Record<string, any>
): Promise<void> {
  await api.post(`/files/${fileId}/dashboard-config`, config)
}

// ── Prompt endpoints ──────────────────────────────────────────────────────────

export async function submitPrompt(
  fileId: string,
  text: string
): Promise<{ prompt_id: string; status: string }> {
  // LLM config headers are required here — the backend task picks the provider from them
  const { data } = await api.post(`/files/${fileId}/prompts`, { text }, {
    headers: llmHeaders(),
  })
  return data
}


export async function clarifyPrompt(
  promptId: string,
  answer: string
): Promise<{ prompt_id: string; status: string }> {
  // LLM config headers forwarded so the re-run uses the same provider/model/key
  const { data } = await api.post(`/prompts/${promptId}/clarify`, { answer }, {
    headers: llmHeaders(),
  })
  return data
}

export async function fetchKPIAggregate(
  fileId: string,
  column: string,
  aggregation: string,
  filters?: Array<{ column: string; operator: string; value: string }>
): Promise<{ value: number }> {
  const params: Record<string, any> = { column, aggregation }
  if (filters && filters.length > 0) {
    params.filters = JSON.stringify(filters)
  }
  const { data } = await api.get(`/files/${fileId}/aggregate`, { params })
  return data
}

export async function fetchUniqueValues(fileId: string, column: string): Promise<string[]> {
  const { data } = await api.get(`/files/${fileId}/unique-values`, { params: { column } })
  return data.values as string[]
}

export async function getHealthConfig() {
  const { data } = await api.get('/health')
  return data
}

export async function fetchCurrentSession() {
  const { data } = await api.get('/files/session/current')
  return data
}

export interface ProviderStatus {
  provider: string
  model:    string
  status:   'online' | 'offline' | 'configured' | 'unknown'
  fallback: string | null
}

export async function getProviderStatus(): Promise<ProviderStatus> {
  const { data } = await api.get('/provider-status')
  return data as ProviderStatus
}

// ── WebSocket factory ─────────────────────────────────────────────────────────

export async function openPromptSocket(promptId: string): Promise<WebSocket> {
  const proto = window.location.protocol === 'https:' ? 'wss' : 'ws'
  let url = `${proto}://${window.location.host}/ws/prompts/${promptId}?session_id=${sessionId}`
  if (keycloak && keycloak.authenticated && keycloak.token) {
    try {
      await keycloak.updateToken(30)
    } catch {
      // Token refresh failed — still attempt with the current token
    }
    url += `&token=${keycloak.token}`
  }
  return new WebSocket(url)
}

// ── Admin endpoints ───────────────────────────────────────────────────────────

export async function fetchAdminUsers(): Promise<any[]> {
  const { data } = await api.get('/platform-users/users')
  return data
}

export async function createAdminUser(payload: any): Promise<void> {
  await api.post('/platform-users/users', payload)
}

export async function updateAdminUser(userId: string, payload: any): Promise<void> {
  await api.put(`/platform-users/users/${userId}`, payload)
}

export async function deleteAdminUser(userId: string): Promise<void> {
  await api.delete(`/platform-users/users/${userId}`)
}

export async function setAdminUserPassword(userId: string, payload: any): Promise<void> {
  await api.put(`/platform-users/users/${userId}/password`, payload)
}
