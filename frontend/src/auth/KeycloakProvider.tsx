import React, { createContext, useContext, useEffect, useState, ReactNode } from 'react'
import Keycloak from 'keycloak-js'

export interface KeycloakContextType {
  keycloak: Keycloak | null
  isAuthenticated: boolean
  isInitialized: boolean
  login: () => void
  logout: () => void
}

const KeycloakContext = createContext<KeycloakContextType>({
  keycloak: null,
  isAuthenticated: false,
  isInitialized: false,
  login: () => { },
  logout: () => { },
})

export const useKeycloak = () => useContext(KeycloakContext)

interface KeycloakProviderProps {
  children: ReactNode
}

// Single instance
export const keycloak = new Keycloak({
  url: window.location.origin,
  realm: 'claria',
  clientId: 'claria-frontend'
})

export const KeycloakProvider: React.FC<KeycloakProviderProps> = ({ children }) => {
  const [isInitialized, setIsInitialized] = useState(false)
  const [isAuthenticated, setIsAuthenticated] = useState(false)
  const didInit = React.useRef(false)

  useEffect(() => {
    // Only initialize once, even in React 18 Strict Mode
    if (didInit.current) return
    didInit.current = true

    const startTime = Date.now()

    // Safety timeout: if Keycloak takes more than 5 seconds, force fail to prevent infinite spinner
    const timeoutId = setTimeout(() => {
      console.warn("Keycloak init timed out after 5 seconds. Forcing initialization.")
      setIsAuthenticated(false)
      setIsInitialized(true)
    }, 5000)

    // PKCE requires HTTPS (crypto.subtle). If we are on HTTP LAN, disable it.
    const supportsPkce = window.isSecureContext && window.crypto && window.crypto.subtle;

    keycloak.init({
      onLoad: 'check-sso',
      silentCheckSsoRedirectUri: window.location.origin + '/silent-check-sso.html',
      pkceMethod: supportsPkce ? 'S256' : undefined,
      checkLoginIframe: false,
      messageReceiveTimeout: 2000,
    }).then((auth) => {
      clearTimeout(timeoutId)
      const elapsed = Date.now() - startTime
      const remaining = Math.max(0, 400 - elapsed)
      setTimeout(() => {
        setIsAuthenticated(auth)
        setIsInitialized(true)
      }, remaining)
    }).catch((e) => {
      clearTimeout(timeoutId)
      setIsAuthenticated(false)
      setIsInitialized(true)
      // Extract a readable message from whatever Keycloak throws (string, Error, or plain object)
      const errMsg = typeof e === 'string'
        ? e
        : (e?.error_description || e?.error || e?.message || JSON.stringify(e))
      console.error("Failed to initialize Keycloak:", errMsg, e)
      // Don't use alert() — it blocks the entire tab. The app already handles
      // unauthenticated state by showing the login button.
    })

    keycloak.onTokenExpired = () => {
      console.log('Token expired, attempting refresh...')
      keycloak.updateToken(30).catch(() => {
        console.error('Failed to refresh token')
        keycloak.logout()
      })
    }
  }, [])

  const login = () => {
    keycloak.login()
  }

  const logout = () => {
    keycloak.logout()
  }

  return (
    <KeycloakContext.Provider value={{ keycloak, isAuthenticated, isInitialized, login, logout }}>
      {children}
    </KeycloakContext.Provider>
  )
}
