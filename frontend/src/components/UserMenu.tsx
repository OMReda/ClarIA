import React, { useState, useRef, useEffect } from 'react'
import { useKeycloak } from '../auth/KeycloakProvider'
import { IconUser, IconLogOut, IconChevronDown, IconSettings } from './Icon'

interface UserMenuProps {
  onNavigate?: (page: 'upload' | 'aski' | 'dashboard' | 'admin') => void;
}

export function UserMenu({ onNavigate }: UserMenuProps = {}) {
  const { keycloak, logout } = useKeycloak()
  const isAdmin = keycloak?.realmAccess?.roles.includes('admin') || false
  const [isOpen, setIsOpen] = useState(false)
  const menuRef = useRef<HTMLDivElement>(null)

  // Get the actual username from Keycloak, fallback to 'Administrateur' or 'Utilisateur'
  const userName = keycloak?.tokenParsed?.preferred_username || (isAdmin ? 'Administrateur' : 'Utilisateur')

  // Close when clicking outside
  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (menuRef.current && !menuRef.current.contains(event.target as Node)) {
        setIsOpen(false)
      }
    }
    if (isOpen) {
      document.addEventListener('mousedown', handleClickOutside)
    }
    return () => {
      document.removeEventListener('mousedown', handleClickOutside)
    }
  }, [isOpen])

  return (
    <div className="user-menu" ref={menuRef} style={{ position: 'relative' }}>
      <button 
        className="btn btn--ghost btn--icon" 
        onClick={() => setIsOpen(!isOpen)}
        style={{ 
          borderRadius: '50%', 
          background: 'var(--bg-secondary)', 
          border: '1px solid var(--border-color)',
          width: '32px', 
          height: '32px',
          color: 'var(--text-secondary)'
        }}
        title="Menu Utilisateur"
      >
        <IconUser size={16} strokeWidth={1.75} />
      </button>

      {isOpen && (
        <div 
          className="user-menu__dropdown"
          style={{
            position: 'absolute',
            top: 'calc(100% + 4px)',
            right: 0,
            background: 'white',
            border: '1px solid var(--border-color)',
            borderRadius: '8px',
            boxShadow: '0 4px 12px rgba(0,0,0,0.1)',
            minWidth: '200px',
            zIndex: 100,
            overflow: 'hidden',
            animation: 'dropdown-pop 0.2s cubic-bezier(0.16, 1, 0.3, 1)',
            transformOrigin: 'top right'
          }}
        >
          <div style={{ padding: '12px 16px', borderBottom: '1px solid var(--border-color)', background: 'var(--bg-secondary)' }}>
            <div style={{ fontSize: '13px', color: 'var(--text-tertiary)', marginBottom: '2px' }}>Connecté en tant que</div>
            <div style={{ fontSize: '14px', fontWeight: 600, color: 'var(--text-primary)', whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>
              {userName}
            </div>
          </div>


          <button
            onClick={() => logout()}
            style={{
              display: 'flex',
              alignItems: 'center',
              gap: '8px',
              width: '100%',
              padding: '12px 16px',
              background: 'transparent',
              border: 'none',
              cursor: 'pointer',
              color: 'var(--status-error)',
              fontSize: '14px',
              fontWeight: 500,
              textAlign: 'left'
            }}
            onMouseOver={(e) => (e.currentTarget.style.background = '#fef2f2')}
            onMouseOut={(e) => (e.currentTarget.style.background = 'transparent')}
          >
            <IconLogOut size={16} strokeWidth={2} />
            Déconnexion
          </button>
        </div>
      )}
    </div>
  )
}
